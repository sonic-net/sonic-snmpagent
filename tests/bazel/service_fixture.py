"""Query an installed SONiC AgentX subagent through private Redis and snmpd."""

import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

import redis


def query_installed_agent(installed, database_template):
    runtime = Path(os.environ['SWSS_RUNTIME_ROOT'])
    programs = {name: runtime / path for name, path in {
        'redis': 'usr/bin/redis-server', 'snmpd': 'usr/sbin/snmpd',
        'get': 'usr/bin/snmpget', 'next': 'usr/bin/snmpgetnext',
    }.items()}
    for path in programs.values():
        assert path.is_file(), path
    processes, logs = [], []
    # Keep Unix paths below sockaddr_un's limit even in deep Bazel sandboxes.
    with tempfile.TemporaryDirectory(prefix='sonic-snmp-', dir='/tmp') as temporary:
        work = Path(temporary)
        env = dict(installed.env, SNMP_PERSISTENT_DIR=str(work / 'persist'), MIBS='')
        (work / 'persist').mkdir()

        def start(name, command):
            log = (work / (name + '.log')).open('w+')
            logs.append(log)
            process = subprocess.Popen(command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
            processes.append(process)
            return process

        def details():
            return '\n'.join(path.name + ':\n' + path.read_text() for path in work.glob('*.log'))

        try:
            redis_socket = work / 'redis.sock'
            # Existing MIBs use both Common's default TCP connector and its
            # explicit Unix connector. Supply both private endpoints.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
                reservation.bind(('127.0.0.1', 0))
                redis_port = reservation.getsockname()[1]
            start('redis', [str(programs['redis']), '--bind', '127.0.0.1',
                            '--port', str(redis_port), '--unixsocket', str(redis_socket),
                            '--save', '', '--appendonly', 'no'])
            client = redis.Redis(unix_socket_path=str(redis_socket), db=4, socket_timeout=1)
            deadline = time.monotonic() + 15
            while True:
                try:
                    if client.ping():
                        break
                except redis.RedisError:
                    if time.monotonic() >= deadline:
                        raise AssertionError(details())
                    time.sleep(.1)
            client.hset('DEVICE_METADATA|localhost', mapping={'hostname': 'bazel-snmp-fixture'})
            database = json.loads(database_template.read_text())
            database['INSTANCES']['redis'].update(port=redis_port, unix_socket_path=str(redis_socket))
            database_file = work / 'database_config.json'
            database_file.write_text(json.dumps(database))
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            agent_socket = work / 'agentx.sock'
            config = work / 'snmpd.conf'
            config.write_text('master agentx\nagentxsocket ' + str(agent_socket) +
                              '\nrocommunity bazel-test 127.0.0.1\n')
            start('snmpd', [str(programs['snmpd']), '-f', '-Lo', '-C', '-c', str(config),
                            '-p', str(work / 'snmpd.pid'), '-I', '-system_mib',
                            'udp:127.0.0.1:' + str(port)])
            launcher = r'''import asyncio,logging,pathlib,sys
logging.basicConfig(level=logging.INFO)
from swsscommon import swsscommon
swsscommon.SonicDBConfig.load_sonic_db_config(sys.argv[1])
from sonic_ax_impl import mibs
mibs.Namespace.db_config_loaded=True
mibs.config(unix_socket_path=sys.argv[2])
from ax_interface import constants
constants.AGENTX_SOCKET_PATH=sys.argv[3]
constants.SNMPD_CONFIG_FILE=sys.argv[4]
from sonic_ax_impl.mibs.ietf.rfc1213 import SysNameMIB
from ax_interface import Agent
import sonic_ax_impl,ax_interface
site=pathlib.Path(sys.argv[5]).resolve()
for module in (sonic_ax_impl,ax_interface):
    assert pathlib.Path(module.__file__).resolve().is_relative_to(site)
loop=asyncio.new_event_loop()
asyncio.set_event_loop(loop)
agent=Agent(SysNameMIB,False,5,loop)
loop.run_until_complete(agent.run_in_event_loop())
'''
            agent = start('agent', [str(installed.python), '-I', '-c', launcher,
                                    str(database_file), str(redis_socket), str(agent_socket),
                                    str(config), str(installed.site)])
            queries = [('get', '.1.3.6.1.2.1.1.5.0'), ('next', '.1.3.6.1.2.1.1.5')]
            results = []
            for operation, oid in queries:
                deadline = time.monotonic() + 30
                while True:
                    result = subprocess.run([str(programs[operation]), '-v2c', '-c', 'bazel-test',
                                             '-On', '-t', '1', '-r', '0',
                                             '127.0.0.1:' + str(port), oid],
                                            cwd=work, env=env, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and 'bazel-snmp-fixture' in result.stdout:
                        assert '.1.3.6.1.2.1.1.5.0' in result.stdout, result.stdout
                        results.append({'operation': operation, 'oid': oid, 'response': result.stdout.strip()})
                        break
                    if time.monotonic() >= deadline or agent.poll() is not None:
                        raise AssertionError(result.stdout + result.stderr + details())
                    time.sleep(.25)
            return {'queries': results, 'services': {key: str(path) for key, path in programs.items()},
                    'scope': 'Installed SysNameMIB via real Common/Redis, AgentX, snmpd, SNMP GET and GETNEXT'}
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for log in logs:
                log.close()
            if 'client' in locals():
                client.close()

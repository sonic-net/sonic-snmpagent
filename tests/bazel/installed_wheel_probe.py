"""Compare the installed SNMP wheel and install TAR with the owner contract."""

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import unittest
import zipfile

from service_fixture import query_installed_agent

from tools.bazel.tests.integration.installed_wheel_fixture import installed_wheels, write_wheel_receipt
from tools.bazel.tests.integration.wheel_contract import normalized_requirement, setup_contract

parser = argparse.ArgumentParser()
for name in ("wheel", "setup", "common-wheel", "install-tar"):
    parser.add_argument("--" + name, type=Path, required=True)
INPUTS, REST = parser.parse_known_args()
DETAILS = {}


class InstalledWheelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wheels = [INPUTS.common_wheel.absolute(), INPUTS.wheel.absolute()]
        cls.setup = INPUTS.setup.absolute()
        import sonic_py_common
        roots = [cls.setup.parent, Path(sonic_py_common.__file__).absolute().parent.parent]
        cls.installed = cls.enterClassContext(installed_wheels(cls.wheels, exclude_source_roots=roots))
        cls.contract = setup_contract(cls.setup)

    def test_complete_payload_and_metadata(self):
        source = self.setup.parent / "src"
        expected = {}
        for package in self.contract["packages"]:
            for path in (source / package.replace(".", "/")).glob("*.py"):
                expected[str(path.relative_to(source))] = path
        for package, patterns in self.contract.get("package_data", {}).items():
            for pattern in patterns:
                for path in (source / package.replace(".", "/")).glob(pattern):
                    if path.is_file():
                        expected[str(path.relative_to(source))] = path
        with zipfile.ZipFile(INPUTS.wheel) as wheel:
            actual = {name for name in wheel.namelist() if ".dist-info/" not in name}
            self.assertEqual(actual, set(expected))
            for member, path in expected.items():
                self.assertEqual(wheel.read(member), path.read_bytes(), member)
                self.assertEqual((self.installed.site / member).read_bytes(), path.read_bytes(), member)
            metadata = BytesParser().parsebytes(wheel.read(next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))))
            self.assertEqual(metadata["Name"], self.contract["name"])
            self.assertEqual(metadata["Version"], self.contract["version"])
            self.assertEqual({normalized_requirement(value) for value in metadata.get_all("Requires-Dist", [])},
                             {normalized_requirement(value) for value in self.contract["install_requires"]})
            self.assertEqual({value.replace("_", "-") for value in metadata.get_all("Provides-Extra", [])}, {"high-perf"})
            license_name = next(name for name in wheel.namelist() if name.endswith("/licenses/LICENSE"))
            self.assertEqual(wheel.read(license_name), (self.setup.parent / "LICENSE").read_bytes())
        DETAILS.update(packages=len(self.contract["packages"]), payload_files=len(expected))

    def test_installed_interfaces_and_entrypoint(self):
        probe = r'''import importlib,importlib.metadata,json,pathlib,sys
site=pathlib.Path(sys.argv[1]).resolve()
modules=['ax_interface','ax_interface.encodings','ax_interface.protocol',
         'sonic_ax_impl','sonic_ax_impl.utils.arg_parser','sonic_py_common']
for name in modules:
    module=importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(site), (name,module.__file__)
from ax_interface.encodings import ObjectIdentifier
value=ObjectIdentifier.from_iterable((1,3,6,1,2,1,1,1,0))
assert str(ObjectIdentifier.from_bytes(value.to_bytes('!'),'!'))=='.1.3.6.1.2.1.1.1.0'
assert importlib.metadata.version('asyncsnmp')=='2.1.0'
print(json.dumps({'installed_modules':modules}))
'''
        result = subprocess.run([str(self.installed.python), "-I", "-c", probe, str(self.installed.site)],
                                cwd=self.installed.root, env=self.installed.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        DETAILS.update(json.loads(result.stdout))
        help_result = subprocess.run([str(self.installed.python), "-I", "-m", "sonic_ax_impl", "--help"],
                                     cwd=self.installed.root, env=self.installed.env,
                                     capture_output=True, text=True, timeout=30)
        self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)
        self.assertIn("Usage:", help_result.stdout)

    def test_real_installed_agentx_queries(self):
        DETAILS["agentx"] = query_installed_agent(self.installed,
            self.setup.parent / "tests/mock_tables/database_config.json")

    def test_exact_install_fragment(self):
        with tarfile.open(INPUTS.install_tar) as archive:
            members = archive.getmembers()
            self.assertEqual([member.name for member in members], ["usr/share/snmp/sysDescr_pass.py"])
            member = members[0]
            self.assertEqual((member.uid, member.gid, member.mode, member.mtime), (0, 0, 0o755, 0))
            self.assertEqual(archive.extractfile(member).read(),
                             (self.setup.parent / "src/sonic_ax_impl/bin/sysDescr_pass.py").read_bytes())
        DETAILS["install_tar_sha256"] = hashlib.sha256(INPUTS.install_tar.read_bytes()).hexdigest()


if __name__ == "__main__":
    result = unittest.main(argv=[__file__, *REST], exit=False).result
    write_wheel_receipt(getattr(InstalledWheelTest, "wheels", None), required=True,
                        status="passed" if result.wasSuccessful() else "failed",
                        details=dict(DETAILS, tests_run=result.testsRun))
    raise SystemExit(not result.wasSuccessful())

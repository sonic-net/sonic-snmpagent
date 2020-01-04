import re
import ipaddress

STATE_CODE = {
    "Idle": 1,
    "Idle (Admin)": 1,
    "Connect": 2,
    "Active": 3,
    "OpenSent": 4,
    "OpenConfirm": 5,
    "Established": 6
};

def parse_bgp_summary(summ):
    ls = summ.splitlines()
    bgpinfo = []

    ## Read until the table header
    n = len(ls)
    li = 0
    while li < n:
        l = ls[li]
        if l.startswith('Neighbor        '):
            break
        if l.startswith('No IPv'): # eg. No IPv6 neighbor is configured, in Quagga (version 0.99.24.1)
            return bgpinfo
        if l.startswith('% No BGP neighbors found'): # in FRRouting (version 7.2)
            return bgpinfo
        if l.endswith('> '): # directly hostname prompt, in FRRouting (version 4.0)
            return bgpinfo
        li += 1

    ## Read and store the table header
    if li >= n:
        raise ValueError('No table header found: ' + summ)
    hl = ls[li]
    li += 1
    ht = re.split('\s+', hl.rstrip())
    hn = len(ht)

    ## Read rows in the table
    while li < n:
        l = ls[li]
        li += 1
        if l == '': break

        ## Handle line wrap
        ## ref: bgp_show_summary in https://github.com/Azure/sonic-quagga/blob/debian/0.99.24.1/bgpd/bgp_vty.c
        if ' ' not in l:
            ## Read next line
            if li >= n:
                raise ValueError('Unexpected line wrap')
            l += ls[li]
            li += 1

        ## Note: State/PfxRcd field may be 'Idle (Admin)'
        lt = re.split('\s+', l.rstrip(), maxsplit = hn - 1)
        if len(lt) != hn:
            raise ValueError('Unexpected row in the table')
        dic = dict(zip(ht, lt))
        bgpinfo.append(dic)
    return bgpinfo

def bgp_peer_tuple(dic):
    nei = dic['Neighbor']
    ver = dic['V']
    sta = dic['State/PfxRcd']

    # prefix '*' appears if the entry is a dynamic neighbor
    nei = nei[1:] if nei[0] == '*' else nei
    ip = ipaddress.ip_address(nei)
    if type(ip) is ipaddress.IPv4Address:
        oid_head = (1, 4)
    else:
        oid_head = (2, 16)

    oid_ip = tuple(i for i in ip.packed)

    if sta.isdigit():
        status = 6
    elif sta in STATE_CODE:
        status = STATE_CODE[sta]
    else:
        return None, None

    return oid_head + oid_ip, status

class QuaggaClient:
    HOST = '127.0.0.1'
    PORT = 2605
    PROMPT_PASSWORD = b'Password: '

    def __init__(self, hostname, sock):
        self.prompt_hostname = ('\r\n' + hostname + '> ').encode()
        self.sock = sock
        self.bgp_provider = 'Quagga'

    def union_bgp_sessions(self):
        bgpsumm_ipv4 = self.show_bgp_summary('ip')
        sessions_ipv4 = parse_bgp_summary(bgpsumm_ipv4)

        bgpsumm_ipv6 = self.show_bgp_summary('ipv6')
        sessions_ipv6 = parse_bgp_summary(bgpsumm_ipv6)

        ## Note: sessions_ipv4 will overwrite sessions_ipv6 if key is the same
        neighbor_sessions = {}
        for ses in sessions_ipv6 + sessions_ipv4:
            nei = ses['Neighbor']
            neighbor_sessions[nei] = ses
        return neighbor_sessions

    def auth(self):
        cmd = b"zebra\n"
        self.sock.send(cmd)

        ## Nowadays we see 2 BGP stack
        ## 1. Quagga (version 0.99.24.1)
        ## 2. FRRouting (version 7.2-sonic)
        banner = self.vtysh_recv()
        if 'Quagga' in banner:
            self.bgp_provider = 'Quagga'
        elif 'FRRouting' in banner:
            self.bgp_provider = 'FRRouting'
        else:
            raise ValueError('Unexpected data recv for banner: {0}'.format(banner))
        return banner

    def vtysh_run(self, command):
        cmd = command.encode() + b'\n'
        self.sock.send(cmd)
        return self.vtysh_recv()

    def vtysh_recv(self):
        acc = b""
        while True:
            data = self.sock.recv(1024)
            if not data:
                raise ValueError('Unexpected data recv: {0}'.format(acc))
            acc += data
            if acc.endswith(self.prompt_hostname):
                break
            if acc.endswith(QuaggaClient.PROMPT_PASSWORD):
                break

        return acc.decode('ascii', 'ignore')

    def show_bgp_summary(self, ipver):
        assert(ipver in ['ip', 'ipv6'])
        if self.bgp_provider == 'Quagga' or ipver == 'ip':
            result = self.vtysh_run('show %s bgp summary' % ipver)
        elif self.bgp_provider == 'FRRouting' and ipver == 'ipv6':
            result = self.vtysh_run('show ip bgp ipv6 summary')
        return result

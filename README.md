## SNMP Subagent

[AgentX](https://www.ietf.org/rfc/rfc2741.txt) implementation for SONiC Switch State Service. See the [SONiC website](http://azure.github.io/SONiC/) for more information on the SONiC project.

MIB implementations included:

* [RFC 1213](https://www.ietf.org/rfc/rfc1213.txt) MIB-II
* [RFC 2737](https://www.ietf.org/rfc/rfc2737.txt) Physical Table MIB
* [RFC 2863](https://www.ietf.org/rfc/rfc2863.txt) Interfaces MIB
* [RFC 3433](https://www.ietf.org/rfc/rfc3433.txt) Sensor Table MIB
* [RFC 4292](https://tools.ietf.org/html/rfc4292) ipCidrRouteDest table in IP Forwarding Table MIB
* [RFC 4363](https://tools.ietf.org/html/rfc4363) dot1qTpFdbPort in Q-BRIDGE-MIB
* [IEEE 802.1 AB](http://www.ieee802.org/1/files/public/MIBs/LLDP-MIB-200505060000Z.txt) LLDP-MIB

To install:
```
$ python3.5 setup.py install
```

To run the daemon:
```
$ python3.5 -m sonic_ax_impl [-d 10]
```


To switch log level of already running snmp-subagent process

1.) Find PID of the process.

```
root 42 1 12 06:37 ? 01:23:46 python3.6 -m sonic_ax_impl
```

2.) Send SIGUSR1 signal to Process
```
root@lnos-x1-a-csw04:/# kill -SIGUSR1 42
```
Sending SIGUSR1 signal to process again will reset the log level. 

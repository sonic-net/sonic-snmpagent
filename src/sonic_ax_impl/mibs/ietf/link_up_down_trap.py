import re

from ax_interface.mib import ValueType
from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from ax_interface.trap import Trap
from ax_interface.encodings import ObjectIdentifier, ValueRepresentation


class linkUpDownTrap(Trap):
    """
    Link up/down SNMP trap handler.

    Logic is fully equivalent to the original implementation,
    including mgmt port behavior.
    Only structure / readability optimized.
    """

    STATUS_MAP = {
        "up": 1,
        "down": 2
    }

    TRAP_OID_MAP = {
        "up":   (1, 3, 6, 1, 6, 3, 1, 1, 5, 4),
        "down": (1, 3, 6, 1, 6, 3, 1, 1, 5, 3)
    }

    IF_RULES = [
        ("PORT_TABLE:Ethernet", lambda k: k[11:], "etherTable"),
        ("LAG_TABLE:PortChannel", lambda k: k[10:], "portChannelTable"),
        ("MGMT_PORT|", lambda k: k.split('|')[1], "mgmtDict"),
        ("MGMT_PORT_TABLE|", lambda k: k.split('|')[1], "mgmtDict"),
    ]

    def __init__(self):
        super().__init__(dbKeys=[
            "__keyspace@0__:LAG_TABLE:PortChannel*",
            "__keyspace@0__:PORT_TABLE:Ethernet*",
            "__keyspace@6__:MGMT_PORT_TABLE|eth*",
            "__keyspace@4__:MGMT_PORT|eth*"
        ])

        self.db_conn = Namespace.init_namespace_dbs()
        Namespace.connect_all_dbs(self.db_conn, mibs.APPL_DB)
        Namespace.connect_all_dbs(self.db_conn, mibs.CONFIG_DB)
        Namespace.connect_all_dbs(self.db_conn, mibs.STATE_DB)

        self.etherTable = {}
        self.portChannelTable = {}
        self.mgmtDict = {}

    def trap_init(self):
        self._init_ethernet_ports()
        self._init_port_channels()
        self._init_mgmt_ports()

    def _init_ethernet_ports(self):
        keys = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "PORT_TABLE:Ethernet*") or []

        for key in keys:
            entry = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, key, blocking=True)
            port_name = key.split("PORT_TABLE:")[-1]
            self.etherTable[port_name] = {
                'admin_status': entry.get('admin_status', 'down'),
                'oper_status': entry.get('oper_status', 'down')
            }

    def _init_port_channels(self):
        keys = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "LAG_TABLE:PortChannel*") or []

        for key in keys:
            entry = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, key, blocking=True)
            portchannel_name = key.split("LAG_TABLE:")[-1]
            self.portChannelTable[portchannel_name] = {
                'admin_status': entry.get('admin_status', 'down'),
                'oper_status': entry.get('oper_status', 'down')
            }

    def _init_mgmt_ports(self):
        # CONFIG DB: admin_status
        config_keys = Namespace.dbs_keys(self.db_conn, mibs.CONFIG_DB, "MGMT_PORT|eth*") or []

        for key in config_keys:
            if_name = key.split('|')[1]
            entry = Namespace.dbs_get_all(self.db_conn, mibs.CONFIG_DB, key, blocking=True)
            self.mgmtDict[if_name] = {
                'admin_status': entry.get('admin_status', 'down'),
                'oper_status': 'down'
            }

        # STATE DB: oper_status
        state_keys = Namespace.dbs_keys(self.db_conn, mibs.STATE_DB, "MGMT_PORT_TABLE|eth*") or []

        for key in state_keys:
            if_name = key.split('|')[1]
            entry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, key, blocking=True)
            if if_name not in self.mgmtDict:
                self.mgmtDict[if_name] = {
                    'admin_status': 'down',
                    'oper_status': entry.get('oper_status', 'down')
                }
            else:
                self.mgmtDict[if_name]['oper_status'] = entry.get('oper_status', 'down')

    def trap_process(self, dbMessage, changedKey):
        genTrap = False

        db_num, actualKey = self._parse_changed_key(changedKey)
        if not actualKey:
            return None

        admin_status, oper_status = self._get_status_from_db(db_num, actualKey)
        if admin_status is None or oper_status is None:
            return None

        if_name, cache = self._match_interface(actualKey)

        cache_key = if_name
        if cache_key not in cache:
            cache[cache_key] = {
                'admin_status': admin_status,
                'oper_status': oper_status
            }
            genTrap = True
        else:
            if (cache[cache_key]['admin_status'] != admin_status or
                    cache[cache_key]['oper_status'] != oper_status):
                cache[cache_key]['admin_status'] = admin_status
                cache[cache_key]['oper_status'] = oper_status
                genTrap = True

        if not genTrap:
            mibs.logger.debug("No change in DB entry, therefore Trap is not generated")
            return None

        return self._build_trap(if_name, admin_status, oper_status)

    def _parse_changed_key(self, changedKey):
        m = re.match(r'__keyspace@(\d+)__:(.*)', changedKey)
        if not m:
            return None, None
        return m.group(1), m.group(2)

    def _get_status_from_db(self, db_num, actualKey):
        try:
            if db_num == '6':  # STATE_DB (mgmt oper)
                entry = Namespace.dbs_get_all(self.db_conn, mibs.STATE_DB, actualKey, blocking=False)
                if not entry:
                    return None, None
                if_name = actualKey.split('|')[1]
                oper_status = entry.get('oper_status', 'down')
                admin_status = self.mgmtDict.get(if_name, {}).get('admin_status', 'down')

            elif db_num == '4':  # CONFIG_DB (mgmt admin)
                entry = Namespace.dbs_get_all(self.db_conn, mibs.CONFIG_DB, actualKey, blocking=False)
                if not entry:
                    return None, None
                if_name = actualKey.split('|')[1]
                admin_status = entry.get('admin_status', 'down')
                oper_status = self.mgmtDict.get(if_name, {}).get('oper_status', 'down')

            else:  # APPL_DB
                entry = Namespace.dbs_get_all(self.db_conn, mibs.APPL_DB, actualKey, blocking=False)
                if not entry:
                    return None, None
                admin_status = entry.get('admin_status', 'down')
                oper_status = entry.get('oper_status', 'down')

            return admin_status, oper_status

        except Exception as e:
            mibs.logger.warning("{}, no Trap generated.".format(e))
            return None, None

    def _match_interface(self, actualKey):
        for prefix, name_fn, cache_name in self.IF_RULES:
            if actualKey.startswith(prefix):
                return name_fn(actualKey), getattr(self, cache_name)
        return None, None

    def _build_trap(self, if_name, admin_status, oper_status):
        if oper_status not in self.TRAP_OID_MAP:
            mibs.logger.warning("Incorrect entry in DB for oper_status, No Trap generated")
            return None

        if_index = mibs.get_index_from_str(if_name)

        varBinds = []

        # ifIndex
        varBinds.append(
            ValueRepresentation(
                ValueType.INTEGER, 0,
                ObjectIdentifier(
                    11, 0, 0, 0,
                    (1, 3, 6, 1, 2, 1, 2, 2, 1, 1, if_index)
                ),
                if_index
            )
        )

        # adminStatus
        varBinds.append(
            ValueRepresentation(
                ValueType.INTEGER, 0,
                ObjectIdentifier(
                    11, 0, 0, 0,
                    (1, 3, 6, 1, 2, 1, 2, 2, 1, 7, if_index)
                ),
                self.STATUS_MAP[admin_status]
            )
        )

        # operStatus
        varBinds.append(
            ValueRepresentation(
                ValueType.INTEGER, 0,
                ObjectIdentifier(
                    11, 0, 0, 0,
                    (1, 3, 6, 1, 2, 1, 2, 2, 1, 8, if_index)
                ),
                self.STATUS_MAP[oper_status]
            )
        )

        return {
            "TrapOid": ObjectIdentifier(10, 0, 0, 0, self.TRAP_OID_MAP[oper_status]),
            "varBinds": varBinds
        }

# Copilot Instructions for sonic-snmpagent

## Project Overview

sonic-snmpagent is an AgentX SNMP subagent for SONiC switches. It implements standard SNMP MIBs by reading data from SONiC's Redis databases and exposing it via the AgentX protocol to the net-snmpd master agent. This enables network monitoring systems to query SONiC switches using standard SNMP protocols.

## Architecture

```
sonic-snmpagent/
├── src/
│   └── sonic_ax_impl/       # Main AgentX implementation
│       ├── main.py           # Agent entry point
│       ├── mibs/             # MIB implementations
│       │   ├── ietf/         # IETF standard MIBs (RFC implementations)
│       │   │   ├── rfc1213.py   # MIB-II
│       │   │   ├── rfc2737.py   # Physical Table MIB
│       │   │   ├── rfc2863.py   # Interfaces MIB
│       │   │   ├── rfc3433.py   # Sensor Table MIB
│       │   │   ├── rfc4292.py   # IP Forwarding Table MIB
│       │   │   └── rfc4363.py   # Q-BRIDGE-MIB
│       │   └── vendor/       # Vendor-specific MIBs
│       └── ...
├── tests/                    # pytest unit tests
├── setup.py                  # Package setup
└── .github/                  # GitHub configuration
```

### Key Concepts
- **AgentX protocol**: Subagent communicates with net-snmpd master agent
- **MIB implementations**: Each MIB class maps OIDs to SONiC Redis data
- **Redis data source**: Reads from STATE_DB, COUNTERS_DB, CONFIG_DB, APP_DB
- **OID tree**: MIB objects are organized in a tree structure with numeric OIDs
- **Dynamic log level**: Send SIGUSR1 to toggle debug logging at runtime

## Language & Style

- **Primary language**: Python 3
- **Indentation**: 4 spaces
- **Naming conventions**:
  - MIB classes: Named after RFC (e.g., `InterfacesMIB`, `PhysicalTableMIB`)
  - Functions: `snake_case`
  - OID constants: `UPPER_CASE`
  - Module files: lowercase or RFC number (e.g., `rfc2863.py`)
- **SNMP style**: Follow the structure of the corresponding RFC for MIB implementation

## Build Instructions

```bash
# Install
python3 setup.py install

# Install for development
pip3 install -e .
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=sonic_ax_impl --cov-report=term-missing
```

- Tests use **pytest**
- Tests mock Redis database responses
- Each MIB class should have corresponding test cases
- Test data mirrors real SONiC DB content

## PR Guidelines

- **Commit format**: `[MIB/component]: Description`
- **Signed-off-by**: REQUIRED (`git commit -s`)
- **CLA**: Sign Linux Foundation EasyCLA
- **RFC compliance**: MIB implementations must strictly follow the relevant RFC
- **Testing**: Include tests with mock DB data for all new MIB objects

## Common Patterns

### MIB Implementation Pattern
```python
class MyMIB(MIBUpdater):
    """Implementation of MY-MIB"""
    
    def __init__(self):
        super().__init__()
        self.db_conn = SonicV2Connector()
        self.db_conn.connect(self.db_conn.COUNTERS_DB)
    
    def update_data(self):
        """Refresh data from Redis"""
        self.data = self.db_conn.get_all(
            self.db_conn.COUNTERS_DB, 'COUNTERS:oid:0x...')
    
    def get_value(self, oid):
        """Return SNMP value for given OID"""
        # Map OID to data field
        return self.data.get(field_name)
```

### OID Registration
```python
# Register OID subtree with the AgentX master
# OIDs follow standard MIB tree structure
# e.g., 1.3.6.1.2.1.2.2.1 for ifTable
```

## Dependencies

- **net-snmp / python-agentx**: AgentX protocol implementation
- **sonic-py-common**: Common SONiC utilities
- **python-swsscommon**: Redis database bindings
- **Redis**: Data source for all MIB values

## Gotchas

- **OID ordering**: SNMP walks require OIDs in strict lexicographic order — incorrect ordering breaks SNMP walks
- **Performance**: SNMP polling can be frequent — cache data appropriately, don't query Redis on every SNMP GET
- **Data freshness**: Cached data must be refreshed at reasonable intervals
- **Counter types**: SNMP Counter32/Counter64 have specific wrapping behavior — handle correctly
- **Multi-ASIC**: Must handle namespace-aware DB connections for multi-ASIC platforms
- **ifIndex mapping**: Interface index mapping must be consistent with SONiC's interface naming
- **MIB compliance**: RFC MIBs have mandatory objects — implement ALL mandatory fields
- **SIGUSR1 debug**: The daemon supports runtime log-level toggle via SIGUSR1 signal

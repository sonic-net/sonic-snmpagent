"""Export upstream resolution state as the reviewed test-service input lock."""
import json
from pathlib import Path
root = Path(__file__).resolve().parent
matches = []
def visit(value):
    if isinstance(value, dict):
        if "lock_content" in value:
            lock = json.loads(value["lock_content"])
            if "snmp_test_services" in lock.get("dependency_sets", {}):
                matches.append(lock)
        for child in value.values():
            visit(child)
    elif isinstance(value, list):
        for child in value:
            visit(child)
visit(json.loads((root / "MODULE.bazel.lock").read_text()))
assert len(matches) == 1, "Resolve the dedicated refresh module first"
lock = matches[0]
assert set(lock["dependency_sets"]) == {"snmp_test_services"}
assert set(lock["dependency_sets"]["snmp_test_services"]["sets"]) == {"amd64"}
lock.pop("facts", None)
lock["_generated"] = {"architecture": "amd64", "generator": "rules_distroless apt.install; export from refresh/MODULE.bazel.lock", "scope": "Private snmpd/snmpget and Redis test services only"}
(root.parent / "apt.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

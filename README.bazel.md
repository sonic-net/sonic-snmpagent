# Bazel source build (AMD64)

The owner exports `//:sonic_snmpagent_wheel` (`asyncsnmp-2.1.0-py3-none-any.whl`),
`//:sonic_snmpagent` (the Python source library), and `//:snmp_install`
(`usr/share/snmp/sysDescr_pass.py`, root-owned, mode 0755, timestamp zero).
The TAR preserves the file installation performed by `python3 -m sonic_ax_impl install`.
No DEB package is produced, and existing Make/setup.py/Debian paths remain available.

```sh
bazel build //:sonic_snmpagent_wheel //:snmp_install
(cd tests/bazel && bazel test //:unit_tests //:installed_wheel_test)
```

Use native Debian Trixie AMD64 and Python 3.13 for the test application. The
Common binding's declared Trixie native libraries are not a compatible loader
runtime for an Ubuntu host. CI runs inside the pinned Trixie container.

The wheel preserves setup.py's package selection, package data, version,
Requires-Dist and empty `high_perf` extra. Add new Python files under `src/`;
Bazel selects them directly, and CI compares the complete wheel with setup.py.
Update both definitions when changing package metadata or install destinations.
The install TAR has no native ELF files, so it needs no debug-symbol TAR.

Production applications supply the existing SWSS Common binding and
`sonic-py-common` owner interfaces. Runtime `natsort`, `psutil` and
`python-arptable` inputs are locked in the source module. The historical wheel
metadata declares only psutil and python-arptable; this change preserves that
contract rather than claiming that pip alone supplies the whole SONiC runtime.
Platform-common is an independent `docker-snmp` runtime dependency, not a source
or import dependency of this SNMP wheel.

`tests/bazel` is a separate test application pinned to the merged sonic-buildimage
PR #64 source revision. It reuses py-common, Common and the existing installed-wheel
fixture instead of recreating their rules. That development root is not a production
module dependency. The original suite retains its mocks, data and assertions (419 passing tests and seven existing multi-namespace skips at this baseline); its
legacy `swsssdk` mock adapter is built from the exact owner source revision selected
by that image baseline, as a test-only locked pip input.

The installed test checks all package/data bytes, dependency metadata, the
entrypoint help, AgentX encoding, and the install TAR. A private Redis instance
supplies a hostname to the installed owner's real SysNameMIB; a private snmpd
receives its AgentX registration and answers actual SNMP GET and GETNEXT requests.
Each service uses a temporary socket/configuration and is terminated in cleanup.
This is an installed component test, not a claim that every SNMP Docker path has
already migrated or that physical hardware was exercised. CI retains the exact
wheel/TAR hashes, original test inventory, query responses, module graphs and
generated Bazel lockfiles.

The test-service APT lock uses Debian's existing Trixie snapshots and imports
pinned snmp/snmpd/Redis packages; it does not define another compilation-tool set.
To refresh deliberately, review the snapshots and selections in
`tests/bazel/refresh/MODULE.bazel`, then run:

```sh
(cd tests/bazel/refresh && bazel build @snmp_test_services//snmp @snmp_test_services//snmpd @snmp_test_services//redis-server)
python3 tests/bazel/refresh/export_lock.py
```

Review the changed versions, archive hashes and transitive package closure, then
rerun the installed test. Ordinary builds consume `tests/bazel/apt.lock.json`
directly and do not resolve the refresh workspace.

"""
Root conftest.py — ensures the local src/ directory is on sys.path before
pytest collects any test modules.

On trixie+ builds the wheel build flow is:
    pip install ".[testing]" → pip uninstall asyncsnmp → python -m pytest
After uninstall, sonic_ax_impl / ax_interface are no longer in site-packages.
Individual test files add src/ to sys.path, but tests/mock_tables/dbconnector.py
(imported during collection) does `import sonic_ax_impl.mibs` before any test
file executes.  Placing the path fixup here resolves the import for all
collectors.
"""
import os
import sys

_src = os.path.join(os.path.dirname(__file__), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

"""Run the complete owner suite with its original mocks and declared inputs."""

import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest


def main():
    source = Path(sys.argv[1]).absolute().parent
    output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    # The original tests create files next to fixtures. Copy only declared owner
    # inputs so neither a writable checkout nor generated host files are needed.
    with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as temporary:
        work = Path(temporary)
        for child in source.iterdir():
            if child.name in ("src", "tests"):
                shutil.copytree(child, work / child.name)
        for name in ("pytest.ini", "setup.cfg"):
            shutil.copyfile(source / name, work / name)
        os.chdir(work)
        sys.path.insert(0, str(work / "src"))
        sys.path.insert(0, str(work))
        report = output / "pytest.xml"
        status = pytest.main([
            "-o", "addopts=", "-v", "--cov=src",
            "--cov-report=xml:" + str(output / "coverage.xml"),
            "--cov-report=term", "--junitxml=" + str(report),
            "tests",
        ])
        summary = {}
        if report.exists():
            root = ET.parse(report).getroot()
            cases = root.findall(".//testcase")
            summary = {
                "tests": len(cases),
                "failures": len(root.findall(".//failure")),
                "errors": len(root.findall(".//error")),
                "skipped": len(root.findall(".//skipped")),
                "inventory": [case.attrib for case in cases],
            }
        (output / "source-tests.json").write_text(json.dumps({
            "status": "passed" if status == 0 else "failed",
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "source": str(source),
            "selection": ["tests"],
            **summary,
        }, indent=2) + "\n")
        if not summary.get("tests"):
            raise RuntimeError("The original suite produced no test inventory")
        return int(status)


if __name__ == "__main__":
    raise SystemExit(main())

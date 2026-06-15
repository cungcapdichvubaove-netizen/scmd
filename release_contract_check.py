# -*- coding: utf-8 -*-
"""
SCMD Pro - Release Contract Validator Proxy
-------------------------------------------
Root-level compatibility entrypoint. The implementation SSOT lives in
``scripts/release_contract_check.py``. This proxy loads that file by absolute
path so it works in normal repositories, extracted audit ZIPs, and environments
without a .git directory.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def main():
    # Prevent this compatibility proxy from generating scripts/__pycache__/
    # while loading the implementation module. The release validator scans the
    # extracted source tree for forbidden artifacts, so it must not create the
    # very bytecode files it is designed to reject.
    sys.dont_write_bytecode = True
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    project_root = Path(__file__).resolve().parent
    script_path = project_root / "scripts" / "release_contract_check.py"
    if not script_path.exists():
        raise SystemExit(f"Missing release validator implementation: {script_path}")

    spec = spec_from_file_location("scmd_release_contract_check_impl", script_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load release validator implementation: {script_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main()


if __name__ == "__main__":
    sys.exit(main())

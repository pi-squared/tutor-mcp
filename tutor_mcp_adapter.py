#!/usr/bin/env python3
"""
Simple Python adapter for tutor-mcp.

Behavior:
 - If TUTOR_MCP_BINARY is set and executable, use that.
 - Else if a 'tutor-mcp' binary exists on PATH or next to this script, exec it.
 - Else if `go` is available and the repository sources are present, run `go build -o tutor-mcp`
   in this script's directory and exec the produced binary.
 - The Python process is replaced with the binary via os.execv (so signals are delivered as expected).

Usage:
  python3 tutor_mcp_adapter.py [args...]
Or make executable and run:
  ./tutor_mcp_adapter.py [args...]

Notes:
 - Ensure environment variables required by tutor-mcp (JWT_SECRET, BASE_URL, etc.) are set in the environment.
"""

from __future__ import annotations
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent

def find_binary() -> Optional[str]:
    # 1) explicit env override
    env_path = os.environ.get("TUTOR_MCP_BINARY")
    if env_path:
        p = Path(env_path)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    # 2) on PATH
    which = shutil.which("tutor-mcp")
    if which:
        return which
    # 3) next to this script (common in container images)
    local = SCRIPT_DIR / "tutor-mcp"
    if local.exists() and os.access(local, os.X_OK):
        return str(local)
    return None

def build_binary(target: Path) -> str:
    if not shutil.which("go"):
        raise RuntimeError("Go toolchain not found in PATH; cannot build tutor-mcp")
    print("tutor_mcp_adapter: building tutor-mcp (go build)...", file=sys.stderr)
    # Run go build in the script dir (assumes repository source is here)
    subprocess.check_call(["go", "build", "-o", str(target)], cwd=SCRIPT_DIR)
    target.chmod(0o755)
    return str(target)

def main() -> None:
    binary = find_binary()
    if not binary:
        try:
            target = SCRIPT_DIR / "tutor-mcp"
            binary = build_binary(target)
        except Exception as e:
            print("tutor_mcp_adapter: failed to locate or build tutor-mcp:", e, file=sys.stderr)
            sys.exit(1)

    # Replace the Python process with the tutor-mcp binary so signals are correct.
    args = [binary] + sys.argv[1:]
    print(f"tutor_mcp_adapter: exec -> {args}", file=sys.stderr)
    os.execv(binary, args)  # never returns unless exec fails

if __name__ == "__main__":
    main()

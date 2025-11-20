#!/usr/bin/env python3
"""
rust_project_setup.py
- Detect OS
- Create cargo project (if missing)
- Read dependencies from dependencies.txt
- Add missing dependencies to Cargo.toml
- Run `cargo build` to fetch/install crates
- On each run re-check and repeat missing installs
"""

from __future__ import annotations
import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path
import re
import textwrap

# try import toml, else try to pip install it
try:
    import toml
except Exception:
    print("python toml package not found. Attempting to install via pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "toml"])
    import toml  # type: ignore

# CONFIG
DEPS_FILENAME = "dependencies.txt"   # file listing crates (one per line)
DEFAULT_PROJECT_TYPE = "--bin"       # or "--lib"
CARGO_NEW_FLAGS = DEFAULT_PROJECT_TYPE

# Helpers
def detect_os() -> str:
    s = platform.system()
    if s == "Darwin":
        return "macos"
    if s == "Windows":
        return "windows"
    if s == "Linux":
        return "linux"
    return s.lower()

def check_tool(name: str) -> bool:
    return shutil.which(name) is not None

def run_cmd(cmd: list[str], cwd: Path | None = None, capture_output=False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, text=True, check=False, capture_output=capture_output)

def parse_dep_line(line: str) -> tuple[str, str | None]:
    """
    Accepts:
      serde
      serde:1.0
      serde = "1.0"
      serde="1.0"
    Returns (crate_name, version_or_None)
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return ("", None)
    # serde = "1.0"
    m = re.match(r'^([\w_-]+)\s*=\s*"(.*)"$', line)
    if m:
        return (m.group(1), m.group(2))
    m = re.match(r'^([\w_-]+)\s*:\s*(.*)$', line)
    if m:
        return (m.group(1), m.group(2).strip())
    # just crate name
    m = re.match(r'^([\w_-]+)$', line)
    if m:
        return (m.group(1), None)
    # fallback: split by whitespace
    parts = line.split()
    if parts:
        name = parts[0]
        ver = parts[1] if len(parts) > 1 else None
        return (name, ver)
    return ("", None)

def read_dependencies_file(path: Path) -> list[tuple[str, str | None]]:
    if not path.exists():
        return []
    deps = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            pkg, ver = parse_dep_line(raw)
            if pkg:
                deps.append((pkg, ver))
    return deps

def ensure_project(project_name: str, project_dir: Path) -> None:
    if project_dir.exists() and (project_dir / "Cargo.toml").exists():
        print(f"[ok] Project '{project_name}' already exists at {project_dir}")
        return
    print(f"[info] Creating cargo project '{project_name}'...")
    r = run_cmd(["cargo", "new", project_name, CARGO_NEW_FLAGS])
    if r.returncode != 0:
        print("[error] cargo new failed. Output:")
        print(r.stdout or r.stderr)
        sys.exit(1)
    print("[ok] Project created.")

def load_cargo_toml(path: Path) -> dict:
    data = toml.load(path)
    return data

def save_cargo_toml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        toml.dump(data, f)

def add_dependencies_to_cargo_toml(cargo_toml_path: Path, deps: list[tuple[str, str | None]]) -> list[str]:
    """
    Returns list of crates that were added (new).
    """
    data = {}
    if cargo_toml_path.exists():
        data = load_cargo_toml(cargo_toml_path)
    else:
        data = {"package": {"name": cargo_toml_path.parent.name, "version": "0.1.0"}}

    if "dependencies" not in data:
        data["dependencies"] = {}

    added = []
    for name, ver in deps:
        if name in data["dependencies"]:
            # already present
            continue
        if ver:
            # try convert version to proper string (strip quotes)
            vs = ver.strip().strip('"').strip("'")
            data["dependencies"][name] = vs
        else:
            data["dependencies"][name] = "*"
        added.append(name)

    if added:
        save_cargo_toml(cargo_toml_path, data)
        print(f"[ok] Added dependencies to Cargo.toml: {', '.join(added)}")
    else:
        print("[ok] No new dependencies to add in Cargo.toml.")
    return added

def cargo_build(project_dir: Path) -> bool:
    print("[info] Running `cargo build` to fetch/build dependencies...")
    r = run_cmd(["cargo", "build"], cwd=project_dir, capture_output=True)
    if r.returncode == 0:
        print("[ok] cargo build succeeded.")
        return True
    else:
        print("[error] cargo build failed. Showing output:")
        out = (r.stdout or "") + (r.stderr or "")
        print(out)
        return False

def main():
    # 1) detect OS and tools
    osname = detect_os()
    print(f"[info] Detected OS: {osname}")

    if not check_tool("cargo") or not check_tool("rustc"):
        print("[warning] 'cargo' or 'rustc' not found in PATH.")
        print(textwrap.dedent("""\
            Please install Rust toolchain first:
              curl https://sh.rustup.rs -sSf | sh
            or visit https://rustup.rs
            After installation, re-run this script.
        """))
        # do not abort forcibly; user may still want to create project or edit files
        # But many subsequent steps require cargo.
    # 2) get project name
    if len(sys.argv) >= 2:
        project_name = sys.argv[1]
    else:
        project_name = input("Project name (folder) to create/use: ").strip()
        if not project_name:
            print("No project name provided. Exiting.")
            sys.exit(1)

    project_dir = Path.cwd() / project_name

    # 3) ensure project exists
    ensure_project(project_name, project_dir)

    cargo_toml_path = project_dir / "Cargo.toml"

    # 4) read dependencies file (try project dir first, then current dir)
    deps_file = project_dir / DEPS_FILENAME
    if not deps_file.exists():
        deps_file = Path.cwd() / DEPS_FILENAME

    deps = read_dependencies_file(deps_file)
    if not deps:
        print(f"[info] No dependencies found in {deps_file}. If you want, create it with one crate per line.")
    else:
        print(f"[info] Found {len(deps)} dependency(ies) in {deps_file}")

    # 5) add missing dependencies to Cargo.toml
    added = add_dependencies_to_cargo_toml(cargo_toml_path, deps)

    # 6) run cargo build to fetch crates (this will install missing ones)
    if check_tool("cargo"):
        ok = cargo_build(project_dir)
        if not ok:
            print("[warning] cargo build failed; try running `cargo build` manually to see details.")
    else:
        print("[error] cargo not available; cannot fetch crates.")

    print("[done] Run this script again to re-check and fetch any remaining missing crates.")

if __name__ == "__main__":
    main()

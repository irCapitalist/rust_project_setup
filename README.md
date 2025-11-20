# rust_project_setup
ابزار مینیمال مدیریت و نصب خودکار پروژه راست با کمک پایتون

# Rust Project Setup Script

A Python script to quickly create and manage Rust projects, automatically install dependencies, and re-check missing crates.

---

## Features

- Detects the operating system (Windows, Linux, macOS).
- Creates a new Rust project using `cargo` or uses an existing one.
- Reads a list of dependencies from a `dependencies.txt` file and adds them to `Cargo.toml`.
- Installs/fetches dependencies using `cargo build`.
- Re-checks project and dependencies each time the script runs.

---

## Requirements

- Python 3.x
- Rust toolchain (install via [rustup](https://rustup.rs/))
- `cargo` available in PATH

---

## Setup

1. Clone or download this repository.
2. Create a `dependencies.txt` file in the same directory as the script, listing one crate per line. Example:


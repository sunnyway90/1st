# AGENTS.md

## Cursor Cloud specific instructions

This is a minimal Python learning repository ("我的第一个仓库" / "My First Repository"). It has no external dependencies — only Python 3 standard library is used.

### Running code

- **Run the application:** `python3 hello.py` or import `greet()` from `hello` module
- **Run tests:** `python3 -m unittest test_hello -v`
- **Syntax check:** `python3 -m py_compile <file.py>`

### Notes

- No `requirements.txt` or `pyproject.toml` exists — there are zero external dependencies.
- The VM has Python 3.12 pre-installed at `/usr/bin/python3`. No virtual environment is needed for this repo.
- Tests use the built-in `unittest` module; no test runner installation is required.

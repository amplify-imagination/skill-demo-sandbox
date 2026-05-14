"""Trivial app used as the subject of CI in the Hands-Free Claude series."""
from __future__ import annotations

import os


def greet(name: str) -> str:
    """Return a friendly greeting."""
    if not name:
        raise ValueError("name must not be empty")
    return f"Hello, {name}!"


def main() -> None:
    name = os.environ.get("NAME", "world")
    print(greet(name))


if __name__ == "__main__":
    main()

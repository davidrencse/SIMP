"""Primary SIMP desktop application: the image-carried messenger."""

from __future__ import annotations

from .chat import WireApp, main

__all__ = ["WireApp", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

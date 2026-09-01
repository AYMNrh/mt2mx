from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

SCHEMA_DIR = Path(__file__).resolve().parents[3] / ".private" / "schemas"


@lru_cache(maxsize=8)
def _schema(message_id: str):
    import xmlschema

    return xmlschema.XMLSchema(str(SCHEMA_DIR / f"{message_id}.xsd"))


def schemas_available() -> bool:
    return (SCHEMA_DIR / "pacs.008.001.08.xsd").exists()


def validate(xml_bytes: bytes, message_id: str) -> list[str]:
    """Validate MX XML against the exact schema; return human-readable errors."""
    if not schemas_available():
        raise RuntimeError("private XSD copies are required for validation")
    try:
        _schema(message_id).validate(xml_bytes)
        return []
    except Exception as exc:
        return _flatten_errors(exc)


def _flatten_errors(exc: Exception) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()

    def visit(error: object) -> None:
        path = getattr(error, "path", None)
        message = getattr(error, "reason", None) or str(error).splitlines()[0][:200]
        key = f"{path}|{message}"
        if key in seen:
            return
        seen.add(key)
        lines.append(f"{path}: {message}")

    if isinstance(exc, list):
        for error in exc:
            visit(error)
    elif hasattr(exc, "errors"):
        for error in exc.errors:
            visit(error)
    else:
        visit(exc)
    return lines

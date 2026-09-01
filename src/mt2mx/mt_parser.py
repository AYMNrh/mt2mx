from __future__ import annotations

import re
from typing import Any

FIELD_HEADING = re.compile(
    r"(?m)^\s*(\d+)\.\s+Field\s+([0-9]{2,3}[A-Za-z]?):\s*(.+?)\s*$"
)
TABLE_ROW = re.compile(
    r"^\s*([MO])\s+([0-9]{2,3}[A-Za-z]?)\s+(.+?)\s{2,}(.+?)\s+(\d+)\s*$"
)
SEQUENCE = re.compile(
    r"^\s*(?:Mandatory|Optional)(?:\s+Repetitive)?\s+Sequence\s+([A-Z])(?:\s+(.+?))?\s*$",
    re.I,
)


def _clean_lines(value: str) -> str:
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())


def _section(chunk: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\s*{re.escape(heading)}\s*$\s*(.*?)(?=^\s*(?:PRESENCE|DEFINITION|NETWORK VALIDATED RULES|USAGE RULES|CODES|EXAMPLES?|VALIDATION|FIELD RULES)\s*$|\Z)"
    )
    match = pattern.search(chunk)
    return _clean_lines(match.group(1)) if match else ""


def _table_metadata(text: str) -> dict[int, dict[str, str]]:
    start = re.search(r"(?m)^.*Format Specifications\s*$", text)
    if not start:
        return {}
    end = re.search(r"(?m)^.*M\s*=\s*Mandatory,\s*O\s*=\s*Optional.*$", text[start.end():])
    table = text[start.end(): start.end() + end.end()] if end else text[start.end():]
    current_sequence = ""
    metadata: dict[int, dict[str, str]] = {}
    pending_status = ""
    for raw in table.splitlines():
        line = raw.replace("\f", "").strip("\r")
        seq = SEQUENCE.match(line)
        if seq:
            current_sequence = seq.group(1).upper()
            continue
        if re.match(r"^\s*End of .*Sequence", line, re.I):
            current_sequence = ""
            continue
        status_only = re.match(r"^\s*([MO])\s*$", line)
        if status_only:
            pending_status = status_only.group(1)
            continue
        row = TABLE_ROW.match(line)
        if not row:
            continue
        status, tag, name, content_options, number = row.groups()
        metadata[int(number)] = {
            "status": status or pending_status,
            "tag": tag,
            "name": name.strip(),
            "content_options": content_options.strip(),
            "sequence": current_sequence,
        }
        pending_status = ""
    return metadata


def _options(format_details: str, content_options: str) -> list[str]:
    found = re.findall(r"(?im)^Option\s+([A-Z])\b", format_details)
    if found:
        return list(dict.fromkeys(found))
    if re.fullmatch(r"(?:No letter option,?\s*)?[A-Z](?:\s*,\s*[A-Z])*", content_options or "", re.I):
        return list(dict.fromkeys(re.findall(r"\b([A-Z])\b", content_options.upper())))
    return []


def parse_mt_guide_text(text: str, message_type: str) -> list[dict[str, Any]]:
    """Parse numbered field occurrences from a SWIFT MT Message Reference Guide text export."""
    matches = list(FIELD_HEADING.finditer(text))
    table = _table_metadata(text)
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        occurrence_no = int(match.group(1))
        tag = match.group(2)
        name = match.group(3).strip()
        chunk_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = text[match.end():chunk_end]
        fmt = _section(chunk, "FORMAT")
        presence = _section(chunk, "PRESENCE")
        meta = table.get(occurrence_no, {})
        requiredness = ""
        if re.search(r"\bOptional\b", presence, re.I):
            requiredness = "O"
        elif re.search(r"\bMandatory\b", presence, re.I):
            requiredness = "M"
        else:
            requiredness = meta.get("status", "")
        content_options = meta.get("content_options", "")
        rows.append(
            {
                "message_type": message_type,
                "occurrence_no": occurrence_no,
                "tag": tag,
                "field_name": name,
                "requiredness": requiredness,
                "sequence": meta.get("sequence", ""),
                "content_options": content_options,
                "options": _options(fmt, content_options),
                "format_details": fmt,
                "source_pdf_page": text[:match.start()].count("\f") + 1,
            }
        )
    return rows

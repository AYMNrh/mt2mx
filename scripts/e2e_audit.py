#!/usr/bin/env python3
"""End-to-end chain audit: translated MX XML -> DFR lineage.

For every element path that actually appears in a translated sample output,
join it against the existing 38,912-row DFR mapping and classify the hop:
MATCHED / PATH_NOT_MAPPED / DFR_MESSAGE_NOT_IN_SCOPE.
"""
from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mt2mx.runtime.builder import translate  # noqa: E402
from mt2mx.runtime.validation import schemas_available, validate  # noqa: E402

VERSION_ALIASES = {
    "pacs.008.001.08": "pacs.008.001.14",
    "pacs.009.001.08": "pacs.009.001.13",
    "camt.054.001.08": "camt.054.001.14",
}
DFR_CSV = Path("C:/Users/rhihi/Downloads/DFR final/DFR/tables_iso20022_MX/outputs/mapping/ALL_SOURCE_TO_TABLES.csv")
NAMESPACE = "{http://www.w3.org/XML/1998/namespace}"


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def walk(element: ET.Element, prefix: str, paths: dict[str, str]) -> None:
    """Collect leaf paths with text or attributes, deduplicated per sample."""
    name = localname(element.tag)
    full = f"{prefix}/{name}" if prefix else name
    if element.text and element.text.strip():
        paths.setdefault(full, element.text.strip())
    for attribute, value in element.attrib.items():
        paths.setdefault(f"{full}/@{attribute}", value)
    for child in element:
        walk(child, full, paths)


def load_dfr() -> list[dict[str, str]]:
    with DFR_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def dfr_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row.get("source_message_id", "")),
            str(row.get("source_xpath", "")),
            str(row.get("source_xml_tag", "")),
        )
        index[key].append(row)
    return index


def main() -> dict[str, Any]:
    has_schemas = schemas_available()
    samples = sorted((ROOT / "examples" / "samples").glob("*.mt"))
    dfr_rows = load_dfr()
    index = dfr_index(dfr_rows)
    chain_rows: list[dict[str, Any]] = []
    per_message: dict[str, Counter] = defaultdict(Counter)
    valid_count = 0

    for sample in samples:
        result = translate(sample.read_text(encoding="utf-8"))
        errors = validate(result.xml, result.mx_message_id) if has_schemas else []
        xsd_valid = not errors
        if xsd_valid:
            valid_count += 1
        document = ET.fromstring(result.xml)
        paths: dict[str, str] = {}
        walk(document, "", paths)
        message = result.mx_message_id
        alias = VERSION_ALIASES.get(message, "")

        for path, value in sorted(paths.items()):
            if alias:
                if "/@" in path:
                    parent, attribute = path.rsplit("/", 1)
                    lookups = [(parent, attribute)]
                else:
                    lookups = [(path, path.rsplit("/", 1)[-1])]
                matches = []
                for parent, attribute in lookups:
                    matches.extend(index.get((alias, parent, attribute), []))
                status = "MATCHED" if matches else "PATH_NOT_MAPPED"
            else:
                matches = []
                status = "DFR_MESSAGE_NOT_IN_SCOPE"

            if matches:
                for match in matches:
                    chain_rows.append(
                        {
                            "sample": sample.stem,
                            "source_type": result.source_type,
                            "mx_message_id": message,
                            "xml_path": path,
                            "sample_value": value[:80],
                            "dfr_join_status": "MATCHED",
                            "dfr_source_message_id": match.get("source_message_id", ""),
                            "target_table": match.get("target_table", ""),
                            "target_column": match.get("target_column", ""),
                            "role": match.get("role", ""),
                        }
                    )
            else:
                chain_rows.append(
                    {
                        "sample": sample.stem,
                        "source_type": result.source_type,
                        "mx_message_id": message,
                        "xml_path": path,
                        "sample_value": value[:80],
                        "dfr_join_status": status,
                        "dfr_source_message_id": alias,
                        "target_table": "",
                        "target_column": "",
                        "role": "",
                    }
                )
            per_message[message][status] += 1

    summary = {
        "samples": len(samples),
        "xsd_validation_skipped": not has_schemas,
        "samples_schema_valid": valid_count,
        "xml_paths_total": len(chain_rows),
        "status_counts": dict(Counter(row["dfr_join_status"] for row in chain_rows)),
        "per_message": {message: dict(counter) for message, counter in sorted(per_message.items())},
        "version_aliases": VERSION_ALIASES,
    }
    with (ROOT / "outputs/e2e_lineage_audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample", "source_type", "mx_message_id", "xml_path", "sample_value",
                "dfr_join_status", "dfr_source_message_id", "target_table", "target_column", "role",
            ],
        )
        writer.writeheader()
        writer.writerows(chain_rows)
    with (ROOT / "outputs/e2e_lineage_audit.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    return summary


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))

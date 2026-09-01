from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping


def _source_key(row: Mapping[str, Any]) -> tuple[str, int]:
    message = str(row.get("message_type") or row.get("mt_message") or "")
    number = int(row.get("occurrence_no") or row.get("mt_occurrence_no") or 0)
    return message, number


def build_crosswalk(
    mt_rows: Iterable[Mapping[str, Any]],
    rule_rows: Iterable[Mapping[str, Any]],
    xsd_paths: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    """Validate and enrich curated rule rows against source and target inventories."""
    source = {_source_key(row): dict(row) for row in mt_rows}
    rules = [dict(row) for row in rule_rows]
    covered = {_source_key(row) for row in rules}
    missing = sorted(set(source) - covered)
    if missing:
        rendered = ", ".join(f"{message}#{number}" for message, number in missing)
        raise ValueError(f"uncovered MT occurrences: {rendered}")

    output: list[dict[str, Any]] = []
    for rule in rules:
        key = _source_key(rule)
        if key not in source:
            raise ValueError(f"rule references unknown MT occurrence: {key[0]}#{key[1]}")
        mt = source[key]
        expected_tag = str(mt.get("tag", ""))
        rule_tag = str(rule.get("mt_tag", ""))
        if rule_tag and rule_tag != expected_tag:
            raise ValueError(
                f"rule tag mismatch for {key[0]}#{key[1]}: {rule_tag} != {expected_tag}"
            )

        mx_message = str(rule.get("mx_message_id", ""))
        mx_path = str(rule.get("mx_path", ""))
        action = str(rule.get("mapping_action", ""))
        if mx_path:
            if mx_message not in xsd_paths:
                raise ValueError(f"no XSD inventory for {mx_message}")
            if mx_path not in xsd_paths[mx_message]:
                raise ValueError(
                    f"target path not found in XSD: {mx_message} {mx_path}"
                )
        elif action != "NO_DIRECT_EQUIVALENT":
            raise ValueError(
                f"{key[0]}#{key[1]} has no MX path but action is {action!r}"
            )

        enriched = dict(rule)
        enriched["mt_message"] = key[0]
        enriched["mt_occurrence_no"] = key[1]
        enriched["mt_tag"] = expected_tag
        enriched["mt_field_name"] = mt.get("field_name", "")
        enriched["mt_requiredness"] = mt.get("requiredness", "")
        enriched["mt_sequence"] = mt.get("sequence", "")
        enriched["mt_source_pdf_page"] = mt.get("source_pdf_page", "")
        output.append(enriched)
    return output


def _dfr_lookup_key(message_id: str, mx_path: str) -> tuple[str, str, str]:
    if "/@" in mx_path:
        parent, attribute = mx_path.rsplit("/", 1)
        return message_id, parent, attribute
    return message_id, mx_path, mx_path.rsplit("/", 1)[-1]


def join_dfr(
    crosswalk_rows: Iterable[Mapping[str, Any]],
    dfr_rows: Iterable[Mapping[str, Any]],
    version_aliases: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Join exact MX paths to the existing DFR lineage, retaining unmatched rows."""
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in dfr_rows:
        key = (
            str(row.get("source_message_id", "")),
            str(row.get("source_xpath", "")),
            str(row.get("source_xml_tag", "")),
        )
        index[key].append(dict(row))

    output: list[dict[str, Any]] = []
    for source_row in crosswalk_rows:
        row = dict(source_row)
        message = str(row.get("mx_message_id", ""))
        path = str(row.get("mx_path", ""))
        if not path:
            row["dfr_join_status"] = "NOT_APPLICABLE"
            output.append(row)
            continue
        dfr_message = version_aliases.get(message, "")
        if not dfr_message:
            row["dfr_join_status"] = "DFR_MESSAGE_NOT_IN_SCOPE"
            output.append(row)
            continue
        matches = index.get(_dfr_lookup_key(dfr_message, path), [])
        if not matches:
            row["dfr_join_status"] = "PATH_NOT_MAPPED"
            row["dfr_source_message_id"] = dfr_message
            output.append(row)
            continue
        for match in matches:
            joined = dict(row)
            joined["dfr_join_status"] = "MATCHED"
            joined["dfr_source_message_id"] = match.get("source_message_id", "")
            joined["dfr_source_xpath"] = match.get("source_xpath", "")
            joined["dfr_source_xml_tag"] = match.get("source_xml_tag", "")
            for key, value in match.items():
                if key.startswith("source_"):
                    continue
                joined[f"dfr_{key}"] = value
            output.append(joined)
    return output

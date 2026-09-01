#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from mt2mx.runtime.builder import TranslationResult, translate  # noqa: E402
from mt2mx.runtime.parser import parse_message  # noqa: E402
from mt2mx.runtime.validation import schemas_available, validate  # noqa: E402

SYNTHESIS_MARKERS = [
    ("CLRG", "settlement method"),
    ("sender BIC", "header/agent fallback"),
    ("receiver BIC", "header/agent fallback"),
    ("Sts=BOOK", "camt.054 status"),
    ("BkTxCd=M910", "camt.054 bank transaction code"),
    ("Sts=INFO", "camt.060 request status"),
    ("MT2MX-CANDIDATE", "proprietary code issuer"),
    ("account owner populated", "camt.060 account owner"),
]


CANONICAL_TAGS = {
    "25": "25a", "25P": "25a", "50": "50a", "50A": "50a", "50F": "50a", "50K": "50a",
    "52A": "52a", "52D": "52a", "53A": "53a", "53B": "53a", "53D": "53a",
    "54A": "54a", "54B": "54a", "54D": "54a", "55A": "55a", "55B": "55a", "55D": "55a",
    "56A": "56a", "56C": "56a", "56D": "56a",
    "57A": "57a", "57B": "57a", "57C": "57a", "57D": "57a",
    "58A": "58a", "58D": "58a", "59": "59a", "59A": "59a", "59F": "59a",
}


def canonical(tag: str) -> str:
    return CANONICAL_TAGS.get(tag, tag)


def run() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    samples = sorted((ROOT / "examples" / "samples").glob("*.mt"))
    has_schemas = schemas_available()

    field_rows: list[dict[str, str]] = []
    sample_rows: list[dict[str, Any]] = []
    synthesized: dict[str, int] = {}

    for sample in samples:
        result = translate(sample.read_text(encoding="utf-8"))
        payload = parse_message(sample.read_text(encoding="utf-8"))
        errors = validate(result.xml, result.mx_message_id) if has_schemas else []
        xsd_valid = not errors

        present_tags = [canonical(tag) for tag, _ in payload.fields]
        mapped_tags = {canonical(tag) for tag, _ in result.mapped}
        skipped_tags = {tag for tag, _ in result.skipped}
        for tag, reason in result.skipped:
            field_rows.append({
                "sample": sample.stem,
                "source_type": result.source_type,
                "mt_tag": tag,
                "status": "SKIPPED",
                "detail": reason,
            })
        for tag, path in result.mapped:
            field_rows.append({
                "sample": sample.stem,
                "source_type": result.source_type,
                "mt_tag": tag,
                "status": "MAPPED",
                "detail": path,
            })
        unmapped = [tag for tag in present_tags if tag not in mapped_tags and tag not in skipped_tags]
        for tag in unmapped:
            field_rows.append({
                "sample": sample.stem,
                "source_type": result.source_type,
                "mt_tag": tag,
                "status": "PRESENT_UNMAPPED",
                "detail": "present in MT but not referenced by the builder; review required",
            })
        for warning in result.warnings:
            for marker, label in SYNTHESIS_MARKERS:
                if marker in warning:
                    synthesized[label] = synthesized.get(label, 0) + 1

        sample_rows.append({
            "sample": sample.stem,
            "source_type": result.source_type,
            "mx_message_id": result.mx_message_id,
            "mapped_fields": len(result.mapped),
            "skipped_fields": len(result.skipped),
            "present_unmapped": len(unmapped),
            "warnings": len(result.warnings),
            "xsd_valid": "PASS" if xsd_valid else "FAIL",
            "xsd_errors": len(errors),
        })

    report: dict[str, Any] = {
        "generated_at": generated_at,
        "samples": len(samples),
        "samples_schema_valid": sum(row["xsd_valid"] == "PASS" for row in sample_rows),
        "xsd_validation_skipped": not has_schemas,
        "field_rows": len(field_rows),
        "mapped_rows": sum(row["status"] == "MAPPED" for row in field_rows),
        "skipped_rows": sum(row["status"] == "SKIPPED" for row in field_rows),
        "present_unmapped_rows": sum(row["status"] == "PRESENT_UNMAPPED" for row in field_rows),
        "synthesized_values": synthesized,
        "approval_status": "REVIEW_REQUIRED_CBPR",
    }

    with (ROOT / "outputs/translation_review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample", "source_type", "mt_tag", "status", "detail"])
        writer.writeheader()
        writer.writerows(field_rows)
    with (ROOT / "outputs/translation_review.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    with (ROOT / "outputs/translation_review.md").open("w", encoding="utf-8") as handle:
        handle.write(render_markdown(report, sample_rows, field_rows))
    (ROOT / "docs/translation_review.html").write_text(render_html(report, sample_rows, field_rows), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any], sample_rows: list[dict[str, Any]], field_rows: list[dict[str, str]]) -> str:
    lines = [
        "# MT → MX translation review",
        "",
        f"Generated {report['generated_at']} (UTC). Approval status: **{report['approval_status']}**.",
        "",
        "## Summary",
        "",
        f"- Samples translated: **{report['samples']}**",
        f"- Schema-valid outputs: **{report['samples_schema_valid']}/{report['samples']}**"
        + (" (validation skipped: private XSDs not present)" if report["xsd_validation_skipped"] else ""),
        f"- Field-level rows: {report['field_rows']} (mapped {report['mapped_rows']}, skipped {report['skipped_rows']}, present-unmapped {report['present_unmapped_rows']})",
        "",
        "## Synthesized values (schema-mandated, not present in MT)",
        "",
    ]
    for label, count in sorted(report["synthesized_values"].items()):
        lines.append(f"- {label}: {count}")
    lines += ["", "## Per-sample results", "", "| Sample | MT | MX | Mapped | Skipped | Unmapped | XSD |", "|---|---|---|---|---|---|---|"]
    for row in sample_rows:
        lines.append(
            f"| {row['sample']} | {row['source_type']} | {row['mx_message_id']} | {row['mapped_fields']} "
            f"| {row['skipped_fields']} | {row['present_unmapped']} | {row['xsd_valid']} |"
        )
    lines += ["", "## Field dispositions", "", "| Sample | Tag | Status | Detail |", "|---|---|---|---|"]
    for row in field_rows:
        lines.append(f"| {row['sample']} | :{row['mt_tag']}: | {row['status']} | {row['detail']} |")
    return "\n".join(lines)


def render_html(report: dict[str, Any], sample_rows: list[dict[str, Any]], field_rows: list[dict[str, str]]) -> str:
    sample_table = "".join(
        f"<tr><td>{escape(row['sample'])}</td><td>{escape(row['source_type'])}</td><td><code>{escape(row['mx_message_id'])}</code></td>"
        f"<td>{row['mapped_fields']}</td><td>{row['skipped_fields']}</td><td>{row['present_unmapped']}</td>"
        f"<td><span class='pill {'ok' if row['xsd_valid'] == 'PASS' else 'bad'}'>{row['xsd_valid']}</span></td></tr>"
        for row in sample_rows
    )
    field_table = "".join(
        f"<tr><td>{escape(row['sample'])}</td><td>:<b>{escape(row['mt_tag'])}</b>:</td>"
        f"<td><span class='pill {row['status'].lower()}'>{row['status']}</span></td><td>{escape(row['detail'])}</td></tr>"
        for row in field_rows
    )
    synth = "".join(f"<li><b>{escape(label)}</b>: {count}</li>" for label, count in sorted(report["synthesized_values"].items()))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MT → MX translation review</title><style>
:root{{--bg:#07111f;--panel:#0e1d30;--line:#24415f;--text:#e8f0f8;--muted:#9db0c5;--blue:#38bdf8;--green:#34d399;--amber:#fbbf24;--red:#fb7185}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(160deg,#06101c,#0a1830);color:var(--text);font:15px Arial,sans-serif}}main{{max-width:1180px;margin:auto;padding:20px}}h1{{font-size:clamp(24px,5vw,40px)}}h2{{margin-top:32px}}code{{color:#bde7ff}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:18px 0}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}.card b{{display:block;font-size:26px;color:var(--blue)}}.card span{{color:var(--muted)}}.warning{{border-left:5px solid var(--amber);background:#2a2210;padding:14px;border-radius:8px}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}}table{{border-collapse:collapse;width:100%;min-width:760px}}th,td{{padding:9px;border-bottom:1px solid #1d344e;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#122844;color:#dff4ff}}ul{{line-height:1.6}}.pill{{display:inline-block;padding:3px 7px;border-radius:999px;font-size:11px;font-weight:bold;background:#334155}}.ok,.mapped{{background:#124937;color:#a7f3d0}}.bad{{background:#5f1d2c;color:#fecdd3}}.skipped{{background:#594613;color:#fde68a}}.present_unmapped{{background:#5f1d2c;color:#fecdd3}}footer{{color:var(--muted);margin:34px 0}}
</style></head><body><main>
<h1>MT → MX translation review</h1>
<p class="muted">Generated {escape(report['generated_at'])} (UTC) · {escape(report['approval_status'])}</p>
<p class="warning"><b>Candidate baseline, not CBPR+ production approval.</b> Synthesized values and conditional mappings below are schema-valid but must be approved against the applicable Usage Guidelines before production use.</p>
<div class="cards">
<div class="card"><b>{report['samples']}</b><span>samples translated</span></div>
<div class="card"><b>{report['samples_schema_valid']}/{report['samples']}</b><span>schema-valid</span></div>
<div class="card"><b>{report['mapped_rows']}</b><span>field mappings</span></div>
<div class="card"><b>{report['skipped_rows']}</b><span>skipped (documented)</span></div>
</div>
<h2>Per-sample results</h2><div class="table-wrap"><table><thead><tr><th>Sample</th><th>MT</th><th>MX</th><th>Mapped</th><th>Skipped</th><th>Unmapped</th><th>XSD</th></tr></thead><tbody>{sample_table}</tbody></table></div>
<h2>Synthesized values</h2><ul>{synth or '<li>none</li>'}</ul>
<h2>Field dispositions</h2><div class="table-wrap"><table><thead><tr><th>Sample</th><th>Tag</th><th>Status</th><th>Detail</th></tr></thead><tbody>{field_table}</tbody></table></div>
<footer>Full counts: <code>outputs/translation_review.json</code> · CSV: <code>outputs/translation_review.csv</code></footer>
</main></body></html>"""


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))

# MT → MX → DFR

Evidence-controlled baseline mappings for five SWIFT MT flows into ISO 20022 MX and the existing DFR model.

## Current result

| Flow | MT occurrences | Target |
|---|---:|---|
| MT103 | 23 | `pacs.008.001.08` |
| MT202 | 11 | `pacs.009.001.08` |
| MT202 COV | 19 | `pacs.009.001.08` cover structure |
| MT910 | 9 | `camt.054.001.08` |
| MT920 | 5 | `camt.060.001.05` |
| **Total** | **67** | |

Generated and verified on 2026-09-01:

- **67/67** MT occurrences have a disposition.
- **234** evidence-graded crosswalk rows were produced.
- **233** non-empty MX targets exist in the exact target XSDs.
- **222** rows join exactly to the current MX→DFR mapping.
- **10** `camt.060` rows cannot join because `camt.060` is outside the current DFR source scope.
- **1** valid `camt.054` party-BIC path is not mapped in DFR.
- **1** deliberate gap: MT103 field 51A is message/header context and was not forced into an ISO `Document` path.

## Important status

**This is a complete, structurally validated baseline—not production-approved CBPR+ translation logic.**

The applicable CBPR+ Usage Guidelines and SWIFT Translation Library were not available. Consequently:

- every implementation candidate remains `REVIEW_REQUIRED_CBPR`;
- uncertain relationships are labeled conditional rather than guessed;
- the source register records both missing artifacts as blocking evidence;
- licensed/user-provided PDFs, extracted text, and XSD copies remain private and git-ignored.

## Deliverables

| Artifact | Purpose |
|---|---|
| [`docs/index.html`](docs/index.html) | Mobile-friendly status and review dashboard |
| [`docs/MT_TO_MX_TO_DFR_GUIDE.md`](docs/MT_TO_MX_TO_DFR_GUIDE.md) | Method, controls, decisions, and approval process |
| [`sources/source_manifest.csv`](sources/source_manifest.csv) | Evidence register with filenames, page counts, hashes, and usage status |
| [`outputs/mt_field_inventory.csv`](outputs/mt_field_inventory.csv) | All 67 numbered MT field occurrences |
| [`outputs/mx_target_inventory.csv`](outputs/mx_target_inventory.csv) | Only MX paths referenced by the crosswalk, with XSD type/cardinality |
| [`outputs/mt_to_mx_crosswalk.csv`](outputs/mt_to_mx_crosswalk.csv) | 234 evidence-graded MT→MX candidate rules |
| [`outputs/mt_to_mx_to_dfr_lineage.csv`](outputs/mt_to_mx_to_dfr_lineage.csv) | Exact-path MX→DFR joins and visible gaps |
| [`outputs/review_queue.csv`](outputs/review_queue.csv) | One review record per MT occurrence |
| [`outputs/dq_issue_log.csv`](outputs/dq_issue_log.csv) | Blocking and non-blocking data-quality issues |
| [`outputs/MT_TO_MX_REVIEW.xlsx`](outputs/MT_TO_MX_REVIEW.xlsx) | Formatted multi-sheet review workbook |
| [`outputs/completeness_report.json`](outputs/completeness_report.json) | Machine-readable count reconciliation |

## Evidence grades

- **B:** strong base-standard semantic alignment, often independently corroborated, but not SWIFT-translation approved.
- **C:** plausible conditional mapping requiring rule/profile confirmation.
- **D:** ambiguous relationship or context-sensitive selection requiring explicit SME decision.

No row is grade A because no applicable official translation-rule export was available.

## Rebuild locally

The committed outputs are viewable without licensed sources. Rebuilding requires the private PDFs, private XSD copies, and the existing DFR mapping:

```bash
uv sync --extra build --extra test
uv run python scripts/build.py \
  --pdf-dir "C:/path/to/private/source-pdfs" \
  --text-dir ".private/extracted" \
  --xsd-dir ".private/schemas" \
  --dfr-csv "C:/path/to/ALL_SOURCE_TO_TABLES.csv"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -q
uv run python scripts/verify.py
```

`pdftotext` must be installed for fresh PDF extraction.

## Publication boundary

Never commit:

- source PDFs;
- extracted full text;
- licensed MyStandards/Translation Library exports;
- private XSD copies;
- confidential payment samples.

The repository publishes only code, hashes, concise factual inventories, derived candidate rules, DFR lineage, and review documentation.

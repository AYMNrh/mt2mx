# Source handling

The source pack used to build this repository is included under `sources/official/` because the user confirmed the right to redistribute these documents publicly.

## Registered locally

The source pack contains:

- five SWIFT Standards MT November 2025 Message Reference Guides;
- four ISO 20022/MyStandards Message Definition Reports;
- PMPG cover-payment guidance;
- a historical Category 9 guide;
- an XML-tag reference;
- an ISO 20022 adoption webinar.

`sources/source_manifest.csv` records each file's exact filename, byte size, page count, SHA-256, version/scope, usage status, and distribution status.

## Required but unavailable

Two evidence classes remain blocking:

- applicable CBPR+ Usage Guidelines;
- SWIFT MT/MX Translation Library rules.

They must be obtained through licensed access; none were available in the supplied download pack.

## Local layout

```text
sources/official/  # user-confirmed public source PDFs
.private/
  extracted/   # pdftotext output
  schemas/     # exact target-version XSD copies
  generated/   # full private XML path inventories
  vendor/      # corroborating public repositories
```

The `.gitignore` excludes `.private/`, `sources/private/`, extracted text, and other private artifacts. The explicitly confirmed PDFs under `sources/official/` are tracked.

## Verification

Before any push, run:

```bash
uv run python scripts/verify.py
```

The verifier fails if a private PDF, extracted text file, XSD, or `.private` path is tracked. PDFs are allowed only under `sources/official/`.

# Private source handling

The evidence files used to build this repository are intentionally **not included**.

## Registered locally

The source pack contains:

- five SWIFT Standards MT November 2025 Message Reference Guides;
- four ISO 20022/MyStandards Message Definition Reports;
- PMPG cover-payment guidance;
- a historical Category 9 guide;
- an XML-tag reference;
- an ISO 20022 adoption webinar.

`sources/source_manifest.csv` records each file's exact filename, byte size, page count, SHA-256, version/scope, usage status, and distribution restriction.

## Required but unavailable

Two evidence classes remain blocking:

- applicable CBPR+ Usage Guidelines;
- SWIFT MT/MX Translation Library rules.

They must be obtained through licensed access and kept outside the public repository.

## Local layout

```text
.private/
  extracted/   # pdftotext output
  schemas/     # exact target-version XSD copies
  generated/   # full private XML path inventories
  vendor/      # corroborating public repositories
```

The `.gitignore` excludes this entire tree plus all `*.pdf`, `*.txt`, and private source paths.

## Verification

Before any push, run:

```bash
uv run python scripts/verify.py
```

The verifier fails if a PDF, extracted text file, XSD, or `.private` path is tracked.

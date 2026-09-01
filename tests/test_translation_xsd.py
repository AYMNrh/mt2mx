from pathlib import Path

import pytest

from mt2mx.runtime.builder import translate
from mt2mx.runtime.validation import schemas_available, validate

SAMPLES = sorted((Path(__file__).parents[1] / "examples" / "samples").glob("*.mt"))

pytestmark = pytest.mark.skipif(
    not schemas_available(), reason="private XSD copies not present; run build extraction first"
)


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.stem)
def test_sample_translates_to_schema_valid_xml(sample: Path):
    result = translate(sample.read_text(encoding="utf-8"))
    errors = validate(result.xml, result.mx_message_id)
    assert not errors, f"{sample.name}: {errors}"


def test_fx_sample_carries_expected_optional_values():
    sample = next(p for p in SAMPLES if p.stem == "mt103_fx")
    result = translate(sample.read_text(encoding="utf-8"))
    xml = result.xml.decode("utf-8")
    assert "PHOB" in xml or "InstrForCdtrAgt" in xml
    assert "camt" not in xml
    assert "1.2345" in xml
    assert "CRED" in xml  # 71A BEN -> CRED
    assert result.warnings, "FX sample should surface conditional warnings"

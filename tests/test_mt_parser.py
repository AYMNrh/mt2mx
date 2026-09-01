from mt2mx.mt_parser import parse_mt_guide_text


GUIDE = '''Standards MT November 2025
MT 202 COV Format Specifications
Status Tag Field Name Content/Options No.
Mandatory Sequence A General Information
M  20 Transaction Reference Number  16x  1
O  52a Ordering Institution  A, D  5
End of Mandatory Sequence A General Information
Mandatory Sequence B Underlying Customer Credit Transfer Details
M  50a Ordering Customer  A, F, K  12
O  52a Ordering Institution  A, D  13
End of Mandatory Sequence B Underlying Customer Credit Transfer Details
M = Mandatory, O = Optional
MT 202 COV Field Specifications
1. Field 20: Transaction Reference Number
FORMAT
16x
PRESENCE
Mandatory
5. Field 52a: Ordering Institution
FORMAT
Option A
[/1!a][/34x]4!a2!a2!c[3!c]
Option D
[/1!a][/34x]4*35x
PRESENCE
Optional
12. Field 50a: Ordering Customer
FORMAT
Option A
[/34x]4!a2!a2!c[3!c]
Option F
35x
Option K
35x
PRESENCE
Mandatory
13. Field 52a: Ordering Institution
FORMAT
Option A
[/1!a][/34x]4!a2!a2!c[3!c]
Option D
[/1!a][/34x]4*35x
PRESENCE
Optional
'''


def test_parses_occurrences_sequences_options_and_presence():
    rows = parse_mt_guide_text(GUIDE, "MT202_COV")
    by_no = {row["occurrence_no"]: row for row in rows}

    assert sorted(by_no) == [1, 5, 12, 13]
    assert by_no[1]["tag"] == "20"
    assert by_no[5]["sequence"] == "A"
    assert by_no[12]["sequence"] == "B"
    assert by_no[12]["tag"] == "50a"
    assert by_no[12]["options"] == ["A", "F", "K"]
    assert by_no[12]["requiredness"] == "M"
    assert by_no[13]["tag"] == "52a"
    assert by_no[13]["requiredness"] == "O"
    assert "Option D" in by_no[13]["format_details"]


def test_optional_field_inside_mandatory_sequence_stays_optional():
    guide = GUIDE.replace(
        "PRESENCE\nOptional\n12. Field 50a",
        "PRESENCE\nOptional in mandatory sequence A\n12. Field 50a",
        1,
    )
    rows = parse_mt_guide_text(guide, "MT202_COV")
    by_no = {row["occurrence_no"]: row for row in rows}

    assert by_no[5]["requiredness"] == "O"

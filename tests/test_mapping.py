import pytest

from mt2mx.mapping import build_crosswalk, join_dfr


MT_ROWS = [
    {"message_type": "MTX", "occurrence_no": 1, "tag": "20", "field_name": "Reference"},
    {"message_type": "MTX", "occurrence_no": 2, "tag": "72", "field_name": "Narrative"},
]
RULES = [
    {
        "mt_message": "MTX",
        "mt_occurrence_no": 1,
        "mt_tag": "20",
        "mx_message_id": "demo.001.001.01",
        "mx_path": "Document/Root/Ref",
        "mapping_action": "DIRECT_CANDIDATE",
    },
    {
        "mt_message": "MTX",
        "mt_occurrence_no": 2,
        "mt_tag": "72",
        "mx_message_id": "demo.001.001.01",
        "mx_path": "",
        "mapping_action": "NO_DIRECT_EQUIVALENT",
    },
]


def test_crosswalk_requires_complete_source_coverage_and_valid_paths():
    paths = {"demo.001.001.01": {"Document/Root/Ref"}}
    rows = build_crosswalk(MT_ROWS, RULES, paths)

    assert len(rows) == 2
    assert rows[0]["mt_field_name"] == "Reference"
    assert rows[1]["mapping_action"] == "NO_DIRECT_EQUIVALENT"

    with pytest.raises(ValueError, match="uncovered MT occurrences"):
        build_crosswalk(MT_ROWS, RULES[:1], paths)

    invalid = [{**RULES[0], "mx_path": "Document/Root/DoesNotExist"}, RULES[1]]
    with pytest.raises(ValueError, match="not found in XSD"):
        build_crosswalk(MT_ROWS, invalid, paths)


def test_dfr_join_handles_xml_attributes_on_parent_xpath():
    crosswalk = [
        {
            **RULES[0],
            "mx_message_id": "demo.001.001.01",
            "mx_path": "Document/Root/Amt/@Ccy",
        }
    ]
    dfr = [
        {
            "source_message_id": "demo.001.001.02",
            "source_xpath": "Document/Root/Amt",
            "source_xml_tag": "@Ccy",
            "final_field": "currency",
            "target_table": "fact_payment",
            "target_column": "currency",
            "bridge_table": "",
            "role": "",
            "sequence_no": "0",
            "mapping_type": "1:1",
            "decision": "CORE",
        }
    ]

    rows = join_dfr(crosswalk, dfr, {"demo.001.001.01": "demo.001.001.02"})

    assert rows[0]["dfr_join_status"] == "MATCHED"
    assert rows[0]["dfr_final_field"] == "currency"

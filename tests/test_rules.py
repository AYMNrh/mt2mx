from mt2mx.rules import curated_rules


def test_curated_rules_cover_all_five_message_occurrence_sets():
    expected = {
        **{("MT103", number): None for number in range(1, 24)},
        **{("MT202", number): None for number in range(1, 12)},
        **{("MT202_COV", number): None for number in range(1, 20)},
        **{("MT910", number): None for number in range(1, 10)},
        **{("MT920", number): None for number in range(1, 6)},
    }
    rules = curated_rules()
    covered = {(row["mt_message"], row["mt_occurrence_no"]) for row in rules}

    assert covered == set(expected)
    assert all(row["mt_tag"] for row in rules)
    assert all(row["mapping_action"] for row in rules)
    assert all(row["evidence_grade"] in {"B", "C", "D"} for row in rules)
    assert all(row["validation_status"] for row in rules)

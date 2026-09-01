import pytest

from mt2mx.runtime.parser import MTPayload, parse_message


MT103_FULL = """{1:F01BANKBEBBAXXX0000000000}{2:I103BANKDEFFXXXXN}{4:
:20:TRX98765
:23B:CRED
:32A:260712EUR2500,00
:50K:/DE89370400440532013000
JOHN DOE
123 MAIN STREET
BERLIN
:52A:DEUTDEFF
:57A:CHASUS33
:59:/GB29NWBK60161331926819
ACME TRADING LTD
1 CORPORATE AVENUE
LONDON
:70:INVOICE 998877
:71A:SHA
-}"""

MT202_FULL = """{1:F01BANKBEBBAXXX0000000000}{2:I202BANKDEFFXXXXN}{4:
:20:TRX202002
:21:RELREF202
:32A:251028USD10000,00
:52A:BANKBEBBXXX
:53A:BANKDEFFXXX
:56A:BANKUS33XXX
:57A:BANKFRPPXXX
:58A:BANKGB22XXX
-}"""

MT202COV_FULL = """{1:F01BANKBEBBAXXX0000000000}{2:I202BANKDEFFXXXXN}{4:
:20:TRX202COV001
:21:RELREF001
:32A:251028EUR10000,00
:50K:/123456789
ALICE CUSTOMER
:52A:BANKBEBB
:59:/987654321
BOB BENEFICIARY
:70:PAYMENT FOR INVOICE 12345
:58A:BANKIT33
-}"""

MT910_FULL = """{1:F01BANKDEFFXXXX0000000000}{2:I910BANKBEBBXXXXN}{4:
:20:NOTIF0001
:21:TRX98765
:25:DE89370400440532013000
:32A:260712EUR2500,00
:50K:/DE89370400440532013000
JOHN DOE
:72:/REC/THANKS
-}"""

MT920_FULL = """{1:F01BANKBEBBXXXX0000000000}{2:I920BANKDEFFXXXXN}{4:
:20:REQ000123
:12:940
:25:DE89370400440532013000
:34F:EUR1000,
:34F:EURC500,
-}"""


def test_parses_blocks_and_sender_receiver_bics():
    msg = parse_message(MT103_FULL)
    assert msg.sender_bic == "BANKBEBBAXX"
    assert msg.receiver_bic == "BANKDEFFXXX"
    assert msg.message_type == "MT103"


def test_multiline_field_value_is_fully_captured():
    msg = parse_message(MT103_FULL)
    value = msg.get("50K")
    assert "JOHN DOE" in value
    assert "123 MAIN STREET" in value
    assert "BERLIN" in value
    assert value.startswith("/DE89370400440532013000")


def test_field_order_and_repeated_tags_preserved():
    msg = parse_message(MT920_FULL)
    tags = [tag for tag, _ in msg.fields]
    assert tags == ["20", "12", "25", "34F", "34F"]
    limits = msg.get_all("34F")
    assert limits == ["EUR1000,", "EURC500,"]


def test_cov_detection_from_sequence_b_fields():
    msg = parse_message(MT202COV_FULL)
    assert msg.message_type == "MT202_COV"
    plain = parse_message(MT202_FULL)
    assert plain.message_type == "MT202"


def test_missing_required_block_raises():
    with pytest.raises(ValueError, match="block 4"):
        parse_message("{1:F01BANKBEBBAXXX0000000000}{2:I103BANKDEFFXXXXN}")


def test_message_type_detection_from_block_two():
    msg = parse_message(MT910_FULL)
    assert msg.message_type == "MT910"
    msg = parse_message(MT920_FULL)
    assert msg.message_type == "MT920"

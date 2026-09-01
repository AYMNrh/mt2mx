import pytest
from decimal import Decimal

from mt2mx.runtime.codes import (
    ChargeBearer,
    charge_bearer,
    parse_amount,
    parse_floor_limit,
    parse_value_date,
    request_message_name,
)


def test_amount_comma_decimal():
    assert parse_amount("2500,00") == Decimal("2500.00")
    assert parse_amount("1234,") == Decimal("1234.00")
    assert parse_amount("0,01") == Decimal("0.01")


def test_value_date_sliding_window():
    assert parse_value_date("260712") == "2026-07-12"
    assert parse_value_date("991231") == "1999-12-31"
    assert parse_value_date("000101") == "2000-01-01"


def test_charge_bearer_code_map():
    assert charge_bearer("OUR") == ChargeBearer.DEBT
    assert charge_bearer("BEN") == ChargeBearer.CRED
    assert charge_bearer("SHA") == ChargeBearer.SHAR
    with pytest.raises(ValueError, match="71A"):
        charge_bearer("XXX")


def test_floor_limit_parsing():
    assert parse_floor_limit("EUR1000,") == ("EUR", None, Decimal("1000.00"))
    assert parse_floor_limit("EURD1000,") == ("EUR", "D", Decimal("1000.00"))
    assert parse_floor_limit("EURC500,") == ("EUR", "C", Decimal("500.00"))
    with pytest.raises(ValueError, match="34F"):
        parse_floor_limit("BROKEN")


def test_requested_message_name_map():
    assert request_message_name("940") == "camt.053.001.08"
    assert request_message_name("950") == "camt.053.001.08"
    assert request_message_name("941") == "camt.052.001.08"
    assert request_message_name("942") == "camt.052.001.08"
    with pytest.raises(ValueError, match="12"):
        request_message_name("999")

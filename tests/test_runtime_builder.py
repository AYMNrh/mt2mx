import pytest
import xml.etree.ElementTree as ET

from mt2mx.runtime.builder import TranslationError, translate
from mt2mx.runtime.parser import parse_message
from tests.test_runtime_parser import (
    MT103_FULL,
    MT202COV_FULL,
    MT202_FULL,
    MT910_FULL,
    MT920_FULL,
)

NS103 = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"
NS109 = "urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08"
NS154 = "urn:iso:std:iso:20022:tech:xsd:camt.054.001.08"
NS160 = "urn:iso:std:iso:20022:tech:xsd:camt.060.001.05"


def _root(result):
    return ET.fromstring(result.xml)


def _find(root, ns, *tags):
    node = root
    for tag in tags:
        node = node.find(f"{{{ns}}}{tag}")
        assert node is not None, f"missing {'/'.join(tags)}"
    return node


def _text(root, ns, *tags):
    return (_find(root, ns, *tags).text or "").strip()


def test_mt103_build_core_values():
    result = translate(MT103_FULL)
    assert result.source_type == "MT103"
    assert result.mx_message_id == "pacs.008.001.08"
    root = _root(result)

    assert _text(root, NS103, "FIToFICstmrCdtTrf", "GrpHdr", "MsgId") == "TRX98765"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "GrpHdr", "SttlmInf", "SttlmMtd") == "CLRG"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "GrpHdr", "InstgAgt", "FinInstnId", "BICFI") == "BANKBEBBAXX"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "GrpHdr", "InstdAgt", "FinInstnId", "BICFI") == "BANKDEFFXXX"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "PmtId", "InstrId") == "TRX98765"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "PmtId", "EndToEndId") == "TRX98765"
    amount = _find(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "IntrBkSttlmAmt")
    assert amount.text == "2500.00"
    assert amount.get("Ccy") == "EUR"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "IntrBkSttlmDt") == "2026-07-12"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "ChrgBr") == "SHAR"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "Dbtr", "Nm") == "JOHN DOE"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "DbtrAcct", "Id", "IBAN") == "DE89370400440532013000"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "DbtrAgt", "FinInstnId", "BICFI") == "DEUTDEFF"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "CdtrAgt", "FinInstnId", "BICFI") == "CHASUS33"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "Cdtr", "Nm") == "ACME TRADING LTD"
    assert _text(root, NS103, "FIToFICstmrCdtTrf", "CdtTrfTxInf", "RmtInf", "Ustrd") == "INVOICE 998877"


def test_mt202_build_core_values():
    result = translate(MT202_FULL)
    root = _root(result)
    assert result.source_type == "MT202"
    assert _text(root, NS109, "FICdtTrf", "CdtTrfTxInf", "PmtId", "InstrId") == "TRX202002"
    assert _text(root, NS109, "FICdtTrf", "CdtTrfTxInf", "PmtId", "EndToEndId") == "RELREF202"
    assert _text(root, NS109, "FICdtTrf", "CdtTrfTxInf", "Dbtr", "FinInstnId", "BICFI") == "BANKBEBBXXX"
    assert _text(root, NS109, "FICdtTrf", "CdtTrfTxInf", "IntrmyAgt1", "FinInstnId", "BICFI") == "BANKUS33XXX"
    assert _text(root, NS109, "FICdtTrf", "CdtTrfTxInf", "CdtrAgt", "FinInstnId", "BICFI") == "BANKFRPPXXX"
    assert _text(root, NS109, "FICdtTrf", "CdtTrfTxInf", "Cdtr", "FinInstnId", "BICFI") == "BANKGB22XXX"
    assert _text(root, NS109, "FICdtTrf", "GrpHdr", "SttlmInf", "InstgRmbrsmntAgt", "FinInstnId", "BICFI") == "BANKDEFFXXX"


def test_mt202cov_build_underlying_customer_transfer():
    result = translate(MT202COV_FULL)
    root = _root(result)
    assert result.source_type == "MT202_COV"
    underlying = _find(root, NS109, "FICdtTrf", "CdtTrfTxInf", "UndrlygCstmrCdtTrf")
    assert _text(underlying, NS109, "Dbtr", "Nm") == "ALICE CUSTOMER"
    assert _text(underlying, NS109, "DbtrAcct", "Id", "Othr", "Id") == "123456789"
    assert _text(underlying, NS109, "Cdtr", "Nm") == "BOB BENEFICIARY"
    assert _text(underlying, NS109, "RmtInf", "Ustrd") == "PAYMENT FOR INVOICE 12345"


def test_mt910_build_core_values():
    result = translate(MT910_FULL)
    root = _root(result)
    assert result.source_type == "MT910"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Id") == "NOTIF0001"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Acct", "Id", "IBAN") == "DE89370400440532013000"
    amount = _find(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Ntry", "Amt")
    assert amount.text == "2500.00"
    assert amount.get("Ccy") == "EUR"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Ntry", "CdtDbtInd") == "CRDT"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Ntry", "ValDt", "Dt") == "2026-07-12"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Ntry", "NtryDtls", "TxDtls", "Refs", "EndToEndId") == "TRX98765"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Ntry", "NtryDtls", "TxDtls", "RltdPties", "Dbtr", "Pty", "Nm") == "JOHN DOE"
    assert _text(root, NS154, "BkToCstmrDbtCdtNtfctn", "Ntfctn", "Ntry", "NtryDtls", "TxDtls", "AddtlTxInf") == "/REC/THANKS"


def test_mt920_build_floor_limits():
    result = translate(MT920_FULL)
    root = _root(result)
    assert result.source_type == "MT920"
    assert _text(root, NS160, "AcctRptgReq", "RptgReq", "Id") == "REQ000123"
    assert _text(root, NS160, "AcctRptgReq", "RptgReq", "ReqdMsgNmId") == "camt.053.001.08"
    assert _text(root, NS160, "AcctRptgReq", "RptgReq", "Acct", "Id", "IBAN") == "DE89370400440532013000"
    assert _text(root, NS160, "AcctRptgReq", "RptgReq", "AcctOwnr", "Agt", "FinInstnId", "BICFI") == "BANKBEBBXXX"
    limits = _find(root, NS160, "AcctRptgReq", "RptgReq").findall(f"{{{NS160}}}ReqdTxTp")
    assert len(limits) == 1
    floors = limits[0].findall(f"{{{NS160}}}FlrLmt")
    assert len(floors) == 2
    assert _text(floors[0], NS160, "CdtDbtInd") == "DEBT"
    assert _text(floors[1], NS160, "CdtDbtInd") == "CRED"
    assert floors[1].find(f"{{{NS160}}}Amt").text == "500.00"


def test_missing_mandatory_field_raises():
    broken = MT103_FULL.replace(":32A:260712EUR2500,00", "")
    with pytest.raises(TranslationError, match="32A"):
        translate(broken)


def test_translate_dispatches_by_message_type():
    for payload_text, expected in [
        (MT103_FULL, "pacs.008.001.08"),
        (MT202_FULL, "pacs.009.001.08"),
        (MT202COV_FULL, "pacs.009.001.08"),
        (MT910_FULL, "camt.054.001.08"),
        (MT920_FULL, "camt.060.001.05"),
    ]:
        assert translate(parse_message(payload_text)).mx_message_id == expected

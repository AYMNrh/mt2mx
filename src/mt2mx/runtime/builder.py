from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from mt2mx.runtime.codes import (
    AgentData,
    PartyData,
    charge_bearer,
    parse_32a,
    parse_33b,
    parse_amount,
    parse_floor_limit,
    parse_rate,
    parse_thirteen_c,
    parse_thirteen_d,
    request_message_name,
)
from mt2mx.runtime.parser import MTPayload, parse_message

MESSAGE_IDS = {
    "MT103": "pacs.008.001.08",
    "MT202": "pacs.009.001.08",
    "MT202_COV": "pacs.009.001.08",
    "MT910": "camt.054.001.08",
    "MT920": "camt.060.001.05",
}
ROOT_TAGS = {
    "pacs.008.001.08": "FIToFICstmrCdtTrf",
    "pacs.009.001.08": "FICdtTrf",
    "camt.054.001.08": "BkToCstmrDbtCdtNtfctn",
    "camt.060.001.05": "AcctRptgReq",
}
NS_TMPL = "urn:iso:std:iso:20022:tech:xsd:{message_id}"

INSTRUCTION3_CODES = {"CHQB", "HOLD", "PHOB", "PHOD", "TELB", "TELF"}
INSTRUCTION4_CODES = {"CHQB", "HOLD", "PHOD", "TELB", "TELF"}
CHARGE_BEARER_REQUIRED = ("71A",)


class TranslationError(ValueError):
    """Raised when a message cannot be translated without guessing."""


@dataclass
class TranslationResult:
    source_type: str
    mx_message_id: str
    xml: bytes
    mapped: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _q(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def _add(parent: ET.Element, tag: str, namespace: str, text: Any | None = None) -> ET.Element:
    element = ET.SubElement(parent, _q(namespace, tag))
    if text is not None:
        element.text = str(text)
    return element


def _amount(parent: ET.Element, tag: str, namespace: str, currency: str, value: Decimal) -> ET.Element:
    element = _add(parent, tag, namespace, value)
    element.set("Ccy", currency)
    return element


def _mark(mapped: list[tuple[str, str]], tag: str, path: str) -> None:
    mapped.append((tag, path))


def _require(payload: MTPayload, tag: str) -> str:
    value = payload.get(tag)
    if value is None:
        raise TranslationError(
            f"{payload.message_type} missing mandatory field :{tag}: required for MX construction"
        )
    return value


def _narrative_lines(value: str) -> str:
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())


def _occurrences(payload: MTPayload, family: str) -> list[tuple[str, str]]:
    return [(tag, value) for tag, value in payload.fields if tag[:2] == family[:2]]


def _agent_occurrence(payload: MTPayload, family: str, index: int = 0) -> AgentData | None:
    occurrences = _occurrences(payload, family)
    if index >= len(occurrences):
        return None
    tag, value = occurrences[index]
    option = tag[2:] or None
    return parse_agent_value(value, option)


def _party_occurrence(payload: MTPayload, family: str, index: int = 0) -> PartyData | None:
    occurrences = _occurrences(payload, family)
    if index >= len(occurrences):
        return None
    return parse_party_value(occurrences[index][1])


def _agent_fininst(parent: ET.Element, namespace: str, agent: AgentData, account_parent: ET.Element | None = None) -> None:
    """BranchAndFinancialInstitutionIdentification6 with optional separate account element."""
    fininst = _add(parent, "FinInstnId", namespace)
    if agent.bic:
        _add(fininst, "BICFI", namespace, agent.bic)
    if agent.name:
        _add(fininst, "Nm", namespace, agent.name)
    if agent.address_lines:
        address = _add(fininst, "PstlAdr", namespace)
        for line in agent.address_lines:
            _add(address, "AdrLine", namespace, line)
    if agent.account and account_parent is not None:
        account_id = _add(account_parent, "Id", namespace)
        _add(_add(account_id, "Othr", namespace), "Id", namespace, agent.account)


def _party135(parent: ET.Element, namespace: str, party: PartyData) -> None:
    if party.name:
        _add(parent, "Nm", namespace, party.name)
    if party.address_lines:
        address = _add(parent, "PstlAdr", namespace)
        for line in party.address_lines:
            _add(address, "AdrLine", namespace, line)
    if party.bic:
        party_id = _add(parent, "Id", namespace)
        org = _add(party_id, "OrgId", namespace)
        _add(org, "AnyBIC", namespace, party.bic)


def _party_account(parent: ET.Element, namespace: str, party: PartyData) -> None:
    if not party.account:
        return
    account_id = _add(parent, "Id", namespace)
    if party.account.startswith("DE") and len(party.account) >= 18:
        _add(account_id, "IBAN", namespace, party.account)
    else:
        _add(_add(account_id, "Othr", namespace), "Id", namespace, party.account)


def _pacs_header(
    payload: MTPayload,
    namespace: str,
    root: ET.Element,
    value_date: str,
    amount: Decimal,
    currency: str,
    created_at: str | None,
    mapped: list[tuple[str, str]],
) -> None:
    header = _add(root, "GrpHdr", namespace)
    _add(header, "MsgId", namespace, _require(payload, "20"))
    _mark(mapped, "20", "GrpHdr/MsgId")
    _add(header, "CreDtTm", namespace, created_at or f"{value_date}T00:00:00")
    _add(header, "NbOfTxs", namespace, "1")
    _add(header, "CtrlSum", namespace, amount)
    _amount(header, "TtlIntrBkSttlmAmt", namespace, currency, amount)
    _add(header, "IntrBkSttlmDt", namespace, value_date)
    settlement = _add(header, "SttlmInf", namespace)
    # Documented default: interbank settlement via clearing (CLRG).
    _add(settlement, "SttlmMtd", namespace, "CLRG")
    if payload.sender_bic:
        _add(header, "InstgAgt", namespace).append(
            _fininst_element(namespace, AgentData(bic=payload.sender_bic))
        )
    if payload.receiver_bic:
        _add(header, "InstdAgt", namespace).append(
            _fininst_element(namespace, AgentData(bic=payload.receiver_bic))
        )


def _fininst_element(namespace: str, agent: AgentData) -> ET.Element:
    fininst = ET.Element(_q(namespace, "FinInstnId"))
    if agent.bic:
        _add(fininst, "BICFI", namespace, agent.bic)
    if agent.name:
        _add(fininst, "Nm", namespace, agent.name)
    if agent.address_lines:
        address = _add(fininst, "PstlAdr", namespace)
        for line in agent.address_lines:
            _add(address, "AdrLine", namespace, line)
    return fininst


def build_103(payload: MTPayload, created_at: str | None = None) -> TranslationResult:
    ns = NS_TMPL.format(message_id=MESSAGE_IDS["MT103"])
    mapped: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    warnings: list[str] = []

    for tag in CHARGE_BEARER_REQUIRED:
        if payload.get(tag) is None:
            raise TranslationError(f"MT103 missing mandatory field :{tag}: required for MX construction")

    value_date, currency, amount = parse_32a(_require(payload, "32A"))
    _mark(mapped, "32A", "CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt;GrpHdr/IntrBkSttlmDt")

    document = ET.Element(_q(ns, "Document"))
    root = _add(document, ROOT_TAGS["pacs.008.001.08"], ns)
    _pacs_header(payload, ns, root, value_date, amount, currency, created_at, mapped)

    transaction = _add(root, "CdtTrfTxInf", ns)
    payment_id = _add(transaction, "PmtId", ns)
    _add(payment_id, "InstrId", ns, _require(payload, "20"))
    _mark(mapped, "20", "CdtTrfTxInf/PmtId/InstrId")
    end_to_end = payload.get("21") or payload.get("20")
    _add(payment_id, "EndToEndId", ns, end_to_end)
    if payload.get("21"):
        _mark(mapped, "21", "CdtTrfTxInf/PmtId/EndToEndId")

    _amount(transaction, "IntrBkSttlmAmt", ns, currency, amount)
    _add(transaction, "IntrBkSttlmDt", ns, value_date)

    if payload.get("13C"):
        try:
            code, time_value = parse_thirteen_c(payload.get("13C") or "")
            if code == "CLSTIME":
                _add(_add(transaction, "SttlmTmReq", ns), "CLSTm", ns, time_value)
                _mark(mapped, "13C", "CdtTrfTxInf/SttlmTmReq/CLSTm")
            else:
                skipped.append(("13C", f"code {code} has no confirmed target; offset handling is policy"))
        except ValueError as exc:
            skipped.append(("13C", str(exc)))

    if payload.get("33B"):
        instructed_currency, instructed_amount = parse_33b(payload["33B"])
        _amount(transaction, "InstdAmt", ns, instructed_currency, instructed_amount)
        _mark(mapped, "33B", "CdtTrfTxInf/InstdAmt+Ccy")
    if payload.get("36"):
        _add(transaction, "XchgRate", ns, parse_rate(payload["36"]))
        _mark(mapped, "36", "CdtTrfTxInf/XchgRate")

    _add(transaction, "ChrgBr", ns, charge_bearer(_require(payload, "71A")).value)
    _mark(mapped, "71A", "CdtTrfTxInf/ChrgBr")

    for tag in ("71F", "71G"):
        if payload.get(tag):
            skipped.append(
                (tag, "ChrgsInf requires Agt, which the MT field cannot supply (DQ-009); retained for review")
            )

    debtor = _party_occurrence(payload, "50a")
    if debtor is None:
        raise TranslationError("MT103 missing mandatory field :50a: required for MX construction")
    _party135(_add(transaction, "Dbtr", ns), ns, debtor)
    _party_account(_add(transaction, "DbtrAcct", ns), ns, debtor)
    _mark(mapped, "50a", "CdtTrfTxInf/Dbtr;DbtrAcct")

    debtor_agent = _agent_occurrence(payload, "52a")
    if debtor_agent is None:
        debtor_agent = AgentData(bic=payload.sender_bic)
        warnings.append(":52a: absent; debtor agent populated from block 1 sender BIC")
    else:
        _mark(mapped, "52a", "CdtTrfTxInf/DbtrAgt")
    _agent_fininst(_add(transaction, "DbtrAgt", ns), ns, debtor_agent)

    creditor_agent = _agent_occurrence(payload, "57a")
    if creditor_agent is None:
        creditor_agent = AgentData(bic=payload.receiver_bic)
        warnings.append(":57a: absent; creditor agent populated from block 2 receiver BIC")
    else:
        _mark(mapped, "57a", "CdtTrfTxInf/CdtrAgt")
    _agent_fininst(_add(transaction, "CdtrAgt", ns), ns, creditor_agent)

    creditor = _party_occurrence(payload, "59a")
    if creditor is None:
        raise TranslationError("MT103 missing mandatory field :59a: required for MX construction")
    _party135(_add(transaction, "Cdtr", ns), ns, creditor)
    _party_account(_add(transaction, "CdtrAcct", ns), ns, creditor)
    _mark(mapped, "59a", "CdtTrfTxInf/Cdtr;CdtrAcct")

    if payload.get("23E"):
        code_value = payload["23E"].split("/", 1)[0].strip()
        instructions = _add(transaction, "InstrForCdtrAgt", ns)
        if code_value in INSTRUCTION3_CODES:
            _add(instructions, "Cd", ns, code_value)
        else:
            _add(instructions, "InstrInf", ns, payload["23E"])
            warnings.append(f":23E: code {code_value!r} not in Instruction3Code; carried as unstructured")
        _mark(mapped, "23E", "CdtTrfTxInf/InstrForCdtrAgt")

    if payload.get("72"):
        _add(_add(transaction, "InstrForNxtAgt", ns), "InstrInf", ns, _narrative_lines(payload["72"]))
        _mark(mapped, "72", "CdtTrfTxInf/InstrForNxtAgt/InstrInf")

    if payload.get("26T"):
        purpose = _add(transaction, "Purp", ns)
        _add(purpose, "Prtry", ns, payload["26T"])
        _mark(mapped, "26T", "CdtTrfTxInf/Purp/Prtry")

    if payload.get("77B"):
        regulatory = _add(transaction, "RgltryRptg", ns)
        details = _add(regulatory, "Dtls", ns)
        _add(details, "Inf", ns, _narrative_lines(payload["77B"]))
        warnings.append(":77B: best-effort; structured code/country split and DbtCdtRptgInd require profile review")
        _mark(mapped, "77B", "CdtTrfTxInf/RgltryRptg/Dtls/Inf")

    if payload.get("70"):
        _add(_add(transaction, "RmtInf", ns), "Ustrd", ns, _narrative_lines(payload["70"]))
        _mark(mapped, "70", "CdtTrfTxInf/RmtInf/Ustrd")

    if payload.get("23B"):
        skipped.append(("23B", "bank operation code is profile-dependent; no safe direct element"))
    if payload.get("51A"):
        skipped.append(("51A", "sending institution belongs to message/header context (documented gap)"))

    return TranslationResult("MT103", MESSAGE_IDS["MT103"], _serialize(document), mapped, skipped, warnings)


def build_202(payload: MTPayload, created_at: str | None = None) -> TranslationResult:
    ns = NS_TMPL.format(message_id=MESSAGE_IDS["MT202"])
    mapped: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    warnings: list[str] = []

    value_date, currency, amount = parse_32a(_require(payload, "32A"))
    _mark(mapped, "32A", "CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt")

    document = ET.Element(_q(ns, "Document"))
    root = _add(document, ROOT_TAGS["pacs.009.001.08"], ns)
    _pacs_header(payload, ns, root, value_date, amount, currency, created_at, mapped)

    transaction = _add(root, "CdtTrfTxInf", ns)
    payment_id = _add(transaction, "PmtId", ns)
    _add(payment_id, "InstrId", ns, _require(payload, "20"))
    _mark(mapped, "20", "CdtTrfTxInf/PmtId/InstrId")
    _add(payment_id, "EndToEndId", ns, _require(payload, "21"))
    _mark(mapped, "21", "CdtTrfTxInf/PmtId/EndToEndId")

    _amount(transaction, "IntrBkSttlmAmt", ns, currency, amount)
    _add(transaction, "IntrBkSttlmDt", ns, value_date)

    if payload.get("56a"):
        intermediary = _agent_occurrence(payload, "56a")
        if intermediary:
            _agent_fininst(_add(transaction, "IntrmyAgt1", ns), ns, intermediary)
            _mark(mapped, "56a", "CdtTrfTxInf/IntrmyAgt1")

    debtor = _agent_occurrence(payload, "52a")
    if debtor is None:
        debtor = AgentData(bic=payload.sender_bic)
        warnings.append(":52a: absent; ordering institution populated from block 1 sender BIC")
    else:
        _mark(mapped, "52a", "CdtTrfTxInf/Dbtr")
    _agent_fininst(_add(transaction, "Dbtr", ns), ns, debtor)

    creditor_agent = _agent_occurrence(payload, "57a")
    if creditor_agent:
        _agent_fininst(_add(transaction, "CdtrAgt", ns), ns, creditor_agent)
        _mark(mapped, "57a", "CdtTrfTxInf/CdtrAgt")

    creditor = _agent_occurrence(payload, "58a")
    if creditor is None:
        raise TranslationError("MT202 missing mandatory field :58a: required for MX construction")
    _agent_fininst(_add(transaction, "Cdtr", ns), ns, creditor)
    _mark(mapped, "58a", "CdtTrfTxInf/Cdtr")

    if payload.get("72"):
        _add(_add(transaction, "InstrForNxtAgt", ns), "InstrInf", ns, _narrative_lines(payload["72"]))
        _mark(mapped, "72", "CdtTrfTxInf/InstrForNxtAgt/InstrInf")

    for family, element_name in (("53a", "InstgRmbrsmntAgt"), ("54a", "InstdRmbrsmntAgt")):
        agent = _agent_occurrence(payload, family)
        if agent:
            settlement = root.find(_q(ns, "GrpHdr")).find(_q(ns, "SttlmInf"))
            _agent_fininst(_add(settlement, element_name, ns), ns, agent)
            _mark(mapped, family, f"GrpHdr/SttlmInf/{element_name}")

    if payload.get("13C"):
        try:
            code, time_value = parse_thirteen_c(payload["13C"])
            if code == "CLSTIME":
                _add(_add(transaction, "SttlmTmReq", ns), "CLSTm", ns, time_value)
                _mark(mapped, "13C", "CdtTrfTxInf/SttlmTmReq/CLSTm")
            else:
                skipped.append(("13C", f"code {code} has no confirmed target; offset handling is policy"))
        except ValueError as exc:
            skipped.append(("13C", str(exc)))

    return TranslationResult(payload.message_type, MESSAGE_IDS[payload.message_type], _serialize(document), mapped, skipped, warnings)


def build_202_cov(payload: MTPayload, created_at: str | None = None) -> TranslationResult:
    ns = NS_TMPL.format(message_id=MESSAGE_IDS["MT202_COV"])
    mapped: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    warnings: list[str] = []

    value_date, currency, amount = parse_32a(_require(payload, "32A"))
    _mark(mapped, "32A", "CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt")

    document = ET.Element(_q(ns, "Document"))
    root = _add(document, ROOT_TAGS["pacs.009.001.08"], ns)
    _pacs_header(payload, ns, root, value_date, amount, currency, created_at, mapped)

    transaction = _add(root, "CdtTrfTxInf", ns)
    payment_id = _add(transaction, "PmtId", ns)
    _add(payment_id, "InstrId", ns, _require(payload, "20"))
    _mark(mapped, "20", "CdtTrfTxInf/PmtId/InstrId")
    _add(payment_id, "EndToEndId", ns, _require(payload, "21"))
    _mark(mapped, "21", "CdtTrfTxInf/PmtId/EndToEndId")

    _amount(transaction, "IntrBkSttlmAmt", ns, currency, amount)
    _add(transaction, "IntrBkSttlmDt", ns, value_date)

    if payload.get("56a"):
        intermediary = _agent_occurrence(payload, "56a")
        if intermediary:
            _agent_fininst(_add(transaction, "IntrmyAgt1", ns), ns, intermediary)
            _mark(mapped, "56a", "CdtTrfTxInf/IntrmyAgt1")

    debtor = _agent_occurrence(payload, "52a")
    if debtor is None:
        debtor = AgentData(bic=payload.sender_bic)
        warnings.append(":52a: absent; ordering institution populated from block 1 sender BIC")
    else:
        _mark(mapped, "52a", "CdtTrfTxInf/Dbtr")
    _agent_fininst(_add(transaction, "Dbtr", ns), ns, debtor)

    creditor_agent = _agent_occurrence(payload, "57a")
    if creditor_agent:
        _agent_fininst(_add(transaction, "CdtrAgt", ns), ns, creditor_agent)
        _mark(mapped, "57a", "CdtTrfTxInf/CdtrAgt")

    creditor = _agent_occurrence(payload, "58a")
    if creditor is None:
        raise TranslationError("MT202 COV missing mandatory field :58a: required for MX construction")
    _agent_fininst(_add(transaction, "Cdtr", ns), ns, creditor)
    _mark(mapped, "58a", "CdtTrfTxInf/Cdtr")

    underlying = _add(transaction, "UndrlygCstmrCdtTrf", ns)
    ordering_customer = _party_occurrence(payload, "50a")
    if ordering_customer is None:
        raise TranslationError("MT202 COV missing mandatory field :50a: required for MX construction")
    _party135(_add(underlying, "Dbtr", ns), ns, ordering_customer)
    _party_account(_add(underlying, "DbtrAcct", ns), ns, ordering_customer)
    _mark(mapped, "50a", "CdtTrfTxInf/UndrlygCstmrCdtTrf/Dbtr;DbtrAcct")

    underlying_debtor_agent = _agent_occurrence(payload, "52a", index=1)
    if underlying_debtor_agent:
        _agent_fininst(_add(underlying, "DbtrAgt", ns), ns, underlying_debtor_agent)
        _mark(mapped, "52a", "CdtTrfTxInf/UndrlygCstmrCdtTrf/DbtrAgt")
    else:
        skipped.append(("52a", "sequence B ordering institution absent"))

    underlying_intermediary = _agent_occurrence(payload, "56a", index=1)
    if underlying_intermediary:
        _agent_fininst(_add(underlying, "IntrmyAgt1", ns), ns, underlying_intermediary)
        _mark(mapped, "56a", "CdtTrfTxInf/UndrlygCstmrCdtTrf/IntrmyAgt1")

    underlying_creditor_agent = _agent_occurrence(payload, "57a", index=1)
    if underlying_creditor_agent:
        _agent_fininst(_add(underlying, "CdtrAgt", ns), ns, underlying_creditor_agent)
        _mark(mapped, "57a", "CdtTrfTxInf/UndrlygCstmrCdtTrf/CdtrAgt")
    else:
        skipped.append(("57a", "sequence B account-with institution absent"))

    beneficiary = _party_occurrence(payload, "59a")
    if beneficiary is None:
        raise TranslationError("MT202 COV missing mandatory field :59a: required for MX construction")
    _party135(_add(underlying, "Cdtr", ns), ns, beneficiary)
    _party_account(_add(underlying, "CdtrAcct", ns), ns, beneficiary)
    _mark(mapped, "59a", "CdtTrfTxInf/UndrlygCstmrCdtTrf/Cdtr;CdtrAcct")

    if payload.get("72"):
        _add(_add(underlying, "InstrForNxtAgt", ns), "InstrInf", ns, _narrative_lines(payload["72"]))
        _mark(mapped, "72", "CdtTrfTxInf/UndrlygCstmrCdtTrf/InstrForNxtAgt/InstrInf")
    if payload.get("70"):
        _add(_add(underlying, "RmtInf", ns), "Ustrd", ns, _narrative_lines(payload["70"]))
        _mark(mapped, "70", "CdtTrfTxInf/UndrlygCstmrCdtTrf/RmtInf/Ustrd")
    if payload.get("33B"):
        instructed_currency, instructed_amount = parse_33b(payload["33B"])
        _amount(underlying, "InstdAmt", ns, instructed_currency, instructed_amount)
        _mark(mapped, "33B", "CdtTrfTxInf/UndrlygCstmrCdtTrf/InstdAmt+Ccy")

    if payload.get("13C"):
        try:
            code, time_value = parse_thirteen_c(payload["13C"])
            if code == "CLSTIME":
                _add(_add(transaction, "SttlmTmReq", ns), "CLSTm", ns, time_value)
                _mark(mapped, "13C", "CdtTrfTxInf/SttlmTmReq/CLSTm")
            else:
                skipped.append(("13C", f"code {code} has no confirmed target; offset handling is policy"))
        except ValueError as exc:
            skipped.append(("13C", str(exc)))

    return TranslationResult("MT202_COV", MESSAGE_IDS["MT202_COV"], _serialize(document), mapped, skipped, warnings)






def build_910(payload: MTPayload, created_at: str | None = None) -> TranslationResult:
    ns = NS_TMPL.format(message_id=MESSAGE_IDS["MT910"])
    mapped: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    warnings: list[str] = []

    value_date, currency, amount = parse_32a(_require(payload, "32A"))
    _mark(mapped, "32A", "Ntry/Amt+Ccy;Ntry/ValDt/Dt")
    account = _require(payload, "25a")

    document = ET.Element(_q(ns, "Document"))
    root = _add(document, ROOT_TAGS["camt.054.001.08"], ns)
    header = _add(root, "GrpHdr", ns)
    _add(header, "MsgId", ns, _require(payload, "20"))
    _mark(mapped, "20", "GrpHdr/MsgId")
    _add(header, "CreDtTm", ns, created_at or f"{value_date}T00:00:00")

    notification = _add(root, "Ntfctn", ns)
    _add(notification, "Id", ns, payload.get("20") or "")
    notification_account = _add(notification, "Acct", ns)
    account_id = _add(notification_account, "Id", ns)
    if account.startswith("DE") and len(account) >= 18:
        _add(account_id, "IBAN", ns, account)
    else:
        _add(account_id, "Othr", ns, account)
    _mark(mapped, "25a", "Ntfctn/Acct/Id")

    entry = _add(notification, "Ntry", ns)
    _add(entry, "NtryRef", ns, payload.get("20") or "")
    _amount(entry, "Amt", ns, currency, amount)
    _add(entry, "CdtDbtInd", ns, "CRDT")
    # camt.054.001.08 requires Sts and BkTxCd; MT910 cannot supply them, so
    # schema-mandated values are synthesized and flagged for profile approval.
    _add(_add(entry, "Sts", ns), "Cd", ns, "BOOK")
    if payload.get("13D"):
        try:
            _add(_add(entry, "BookgDt", ns), "DtTm", ns, parse_thirteen_d(payload["13D"]))
            _mark(mapped, "13D", "Ntry/BookgDt/DtTm")
        except ValueError as exc:
            skipped.append(("13D", str(exc)))
    _add(_add(entry, "ValDt", ns), "Dt", ns, value_date)
    # camt.054.001.08 requires Sts and BkTxCd; MT910 cannot supply them, so
    # schema-mandated values are synthesized and flagged for profile approval.
    bank_code = _add(entry, "BkTxCd", ns)
    proprietary = _add(bank_code, "Prtry", ns)
    _add(proprietary, "Cd", ns, "M910")
    _add(proprietary, "Issr", ns, "MT2MX-CANDIDATE")
    warnings.append(
        ":32A: camt.054.001.08 requires Sts and BkTxCd which MT910 cannot supply; "
        "synthesized Sts=BOOK and proprietary BkTxCd=M910 pending profile approval"
    )

    entry_details = _add(entry, "NtryDtls", ns)
    transaction_details = _add(entry_details, "TxDtls", ns)
    references = _add(transaction_details, "Refs", ns)
    _add(references, "EndToEndId", ns, _require(payload, "21"))
    warnings.append(":21: mapped to Refs/EndToEndId as default; reference type depends on the causing message (DQ-004)")
    _mark(mapped, "21", "Ntry/NtryDtls/TxDtls/Refs/EndToEndId")

    related_parties = _add(transaction_details, "RltdPties", ns)
    ordering_customer = _party_occurrence(payload, "50a")
    if ordering_customer:
        debtor = _add(related_parties, "Dbtr", ns)
        party = _add(debtor, "Pty", ns)
        if ordering_customer.name:
            _add(party, "Nm", ns, ordering_customer.name)
        if ordering_customer.address_lines:
            address = _add(party, "PstlAdr", ns)
            for line in ordering_customer.address_lines:
                _add(address, "AdrLine", ns, line)
        if ordering_customer.bic:
            party_id = _add(party, "Id", ns)
            _add(_add(party_id, "OrgId", ns), "AnyBIC", ns, ordering_customer.bic)
        if ordering_customer.account:
            _party_account(_add(related_parties, "DbtrAcct", ns), ns, ordering_customer)
        _mark(mapped, "50a", "Ntry/NtryDtls/TxDtls/RltdPties/Dbtr;DbtrAcct")

    related_agents = _add(transaction_details, "RltdAgts", ns)
    ordering_institution = _agent_occurrence(payload, "52a")
    if ordering_institution:
        _agent_fininst(_add(related_agents, "DbtrAgt", ns), ns, ordering_institution)
        _mark(mapped, "52a", "Ntry/NtryDtls/TxDtls/RltdAgts/DbtrAgt")
    intermediary = _agent_occurrence(payload, "56a")
    if intermediary:
        _agent_fininst(_add(related_agents, "IntrmyAgt1", ns), ns, intermediary)
        _mark(mapped, "56a", "Ntry/NtryDtls/TxDtls/RltdAgts/IntrmyAgt1")

    if payload.get("72"):
        _add(transaction_details, "AddtlTxInf", ns, _narrative_lines(payload["72"]))
        _mark(mapped, "72", "Ntry/NtryDtls/TxDtls/AddtlTxInf")

    return TranslationResult("MT910", MESSAGE_IDS["MT910"], _serialize(document), mapped, skipped, warnings)


def build_920(payload: MTPayload, created_at: str | None = None) -> TranslationResult:
    ns = NS_TMPL.format(message_id=MESSAGE_IDS["MT920"])
    mapped: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    warnings: list[str] = []

    document = ET.Element(_q(ns, "Document"))
    root = _add(document, ROOT_TAGS["camt.060.001.05"], ns)
    header = _add(root, "GrpHdr", ns)
    _add(header, "MsgId", ns, _require(payload, "20"))
    _mark(mapped, "20", "GrpHdr/MsgId;RptgReq/Id")
    _add(header, "CreDtTm", ns, created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))

    request = _add(root, "RptgReq", ns)
    _add(request, "Id", ns, payload.get("20") or "")
    message_name = request_message_name(_require(payload, "12"))
    _add(request, "ReqdMsgNmId", ns, message_name)
    warnings.append(":12: translated to a profile-default message version; exact version is a bilateral/usage decision")
    _mark(mapped, "12", "RptgReq/ReqdMsgNmId")

    account = _require(payload, "25")
    account_element = _add(request, "Acct", ns)
    account_id = _add(account_element, "Id", ns)
    if account.startswith("DE") and len(account) >= 18:
        _add(account_id, "IBAN", ns, account)
    else:
        _add(account_id, "Othr", ns, account)
    _mark(mapped, "25", "RptgReq/Acct/Id")

    owner = _add(request, "AcctOwnr", ns)
    agent = _add(owner, "Agt", ns)
    _add(_add(agent, "FinInstnId", ns), "BICFI", ns, payload.sender_bic)
    warnings.append("account owner populated from block 1 sender BIC; MT920 carries no owner field")

    limits = payload.get_all("34F")
    requested_type: ET.Element | None = None
    for index, raw in enumerate(limits, start=1):
        currency, direction, limit_amount = parse_floor_limit(raw)
        if requested_type is None:
            requested_type = _add(request, "ReqdTxTp", ns)
            # camt.060.001.05 requires Sts and CdtDbtInd inside ReqdTxTp and
            # allows at most one ReqdTxTp per RptgReq; MT920 carries no entry
            # status, so Sts=INFO is synthesized and both floors share the block.
            _add(_add(requested_type, "Sts", ns), "Cd", ns, "INFO")
            warnings.append(
                "ReqdTxTp/Sts=INFO synthesized (MT920 has no entry status); "
                "ReqdTxTp/CdtDbtInd derived from the first floor-limit direction"
            )
            first_direction = limits[0]
            try:
                _, first_dir, _ = parse_floor_limit(first_direction)
            except ValueError:
                first_dir = None
            indicator = {"D": "DBIT", "C": "CRDT"}.get(first_dir, "DBIT")
            _add(requested_type, "CdtDbtInd", ns, indicator)
        limit = _add(requested_type, "FlrLmt", ns)
        _amount(limit, "Amt", ns, currency, limit_amount)
        # FloorLimitType1Code: DEBT/CRED/BOTH; when MT920 C2 leaves the
        # subfield unused, position decides: first 34F is the debit floor.
        floor_indicator = {"D": "DEBT", "C": "CRED"}.get(direction, "DEBT" if index == 1 else "CRED")
        _add(limit, "CdtDbtInd", ns, floor_indicator)
        if direction is None and index > 1:
            warnings.append(f"34F #{index} lacks the D/C subfield required by MT920 C2; credit assumed")
        _mark(mapped, "34F", f"RptgReq/ReqdTxTp/FlrLmt (#{index})")

    return TranslationResult("MT920", MESSAGE_IDS["MT920"], _serialize(document), mapped, skipped, warnings)


def parse_party_value(value: str, options: list[str] | None = None) -> PartyData:
    from mt2mx.runtime.codes import parse_party

    return parse_party(value, options)


def parse_agent_value(value: str, options: list[str] | None = None) -> AgentData:
    from mt2mx.runtime.codes import parse_agent

    return parse_agent(value, options)


def _serialize(document: ET.Element) -> bytes:
    tree = ET.ElementTree(document)
    return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)


BUILDERS = {
    "MT103": build_103,
    "MT202": build_202,
    "MT202_COV": build_202_cov,
    "MT910": build_910,
    "MT920": build_920,
}


def translate(text_or_payload: str | MTPayload, created_at: str | None = None) -> TranslationResult:
    """Translate a SWIFT MT payload into its target MX document."""
    payload = text_or_payload if isinstance(text_or_payload, MTPayload) else parse_message(text_or_payload)
    if payload.message_type not in BUILDERS:
        raise TranslationError(f"no builder for {payload.message_type}")
    return BUILDERS[payload.message_type](payload, created_at)

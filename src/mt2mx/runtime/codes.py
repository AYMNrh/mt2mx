from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from mt2mx.runtime.parser import is_bic, is_iban

AMOUNT_RE = re.compile(r"^[0-9]{1,15}(?:,[0-9]{0,2})$")
FLOOR_LIMIT_RE = re.compile(r"^([A-Z]{3})([DC])?([0-9]{1,15}(?:,[0-9]{0,2})?)$")
THIRTEEN_C_RE = re.compile(r"^/([A-Z0-9]{1,8})/([0-9]{4})([+-])([0-9]{4})$")
THIRTEEN_D_RE = re.compile(r"^([0-9]{6})([0-9]{4})([+-])([0-9]{4})$")
PARTY_SUBFIELD_RE = re.compile(r"^([0-9])/(.*)$")
F32A_RE = re.compile(r"^([0-9]{6})([A-Z]{3})([0-9]{1,15}(?:,[0-9]{0,2})?)$")
F33B_RE = re.compile(r"^([A-Z]{3})([0-9]{1,15}(?:,[0-9]{0,2})?)$")


class ChargeBearer(str, Enum):
    DEBT = "DEBT"
    CRED = "CRED"
    SHAR = "SHAR"


def parse_amount(raw: str) -> Decimal:
    cleaned = raw.replace("\n", "").replace("\r", "").strip()
    if not AMOUNT_RE.match(cleaned):
        raise ValueError(f"malformed SWIFT amount: {raw!r}")
    normalized = cleaned.replace(",", ".")
    if normalized.endswith("."):
        normalized += "00"
    return Decimal(normalized)


def parse_value_date(yymmdd: str) -> str:
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        raise ValueError(f"malformed value date: {yymmdd!r}")
    year = int(yymmdd[:2])
    century = 2000 if year < 80 else 1900
    return f"{century + year:04d}-{yymmdd[2:4]}-{yymmdd[4:6]}"


def parse_thirteen_c(raw: str) -> tuple[str, str]:
    match = THIRTEEN_C_RE.match(raw.strip())
    if not match:
        raise ValueError(f"malformed 13C: {raw!r}")
    code, hhmm, _sign, _offset = match.groups()
    # ISO 20022 ISOTime carries no offset; offset is a conversion-policy item.
    return code, f"{hhmm[:2]}:{hhmm[2:]}:00"


def parse_thirteen_d(raw: str) -> str:
    match = THIRTEEN_D_RE.match(raw.strip())
    if not match:
        raise ValueError(f"malformed 13D: {raw!r}")
    yymmdd, hhmm, sign, offset = match.groups()
    iso_offset = f"{sign}{offset[:2]}:{offset[2:]}"
    return f"{parse_value_date(yymmdd)}T{hhmm[:2]}:{hhmm[2:]}:00{iso_offset}"


def charge_bearer(code: str) -> ChargeBearer:
    mapping = {"OUR": ChargeBearer.DEBT, "BEN": ChargeBearer.CRED, "SHA": ChargeBearer.SHAR}
    if code not in mapping:
        raise ValueError(f"unsupported 71A charge code: {code!r}")
    return mapping[code]


def request_message_name(requested_type: str) -> str:
    mapping = {
        "940": "camt.053.001.08",
        "950": "camt.053.001.08",
        "941": "camt.052.001.08",
        "942": "camt.052.001.08",
    }
    if requested_type not in mapping:
        raise ValueError(f"unsupported MT920 field 12 value: {requested_type!r}")
    return mapping[requested_type]


def parse_floor_limit(raw: str) -> tuple[str, str | None, Decimal]:
    match = FLOOR_LIMIT_RE.match(raw.replace(" ", "").strip())
    if not match:
        raise ValueError(f"malformed 34F floor limit: {raw!r}")
    currency, direction, amount = match.groups()
    return currency, direction, parse_amount(amount)


def parse_32a(raw: str) -> tuple[str, str, Decimal]:
    """Split a 32A value into (ISO date, currency, amount)."""
    match = F32A_RE.match(raw.replace(" ", "").strip())
    if not match:
        raise ValueError(f"malformed 32A: {raw!r}")
    yymmdd, currency, amount = match.groups()
    return parse_value_date(yymmdd), currency, parse_amount(amount)


def parse_33b(raw: str) -> tuple[str, Decimal]:
    """Split a 33B value into (currency, amount)."""
    match = F33B_RE.match(raw.replace(" ", "").strip())
    if not match:
        raise ValueError(f"malformed 33B: {raw!r}")
    currency, amount = match.groups()
    return currency, parse_amount(amount)


def parse_rate(raw: str) -> Decimal:
    """Convert a SWIFT decimal-comma rate into a Decimal."""
    cleaned = raw.replace(" ", "").strip()
    if not cleaned or any(ch not in "0123456789,." for ch in cleaned):
        raise ValueError(f"malformed exchange rate: {raw!r}")
    normalized = cleaned.replace(",", ".")
    if normalized.endswith("."):
        normalized += "0"
    return Decimal(normalized)


@dataclass
class PartyData:
    name: str | None = None
    bic: str | None = None
    account: str | None = None
    address_lines: list[str] | None = None
    other_identifier: str | None = None


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _strip_account(line: str) -> str | None:
    if line.startswith("//"):
        return line[2:]
    if line.startswith("/"):
        return line[1:]
    return None


def parse_party(value: str, options: list[str] | None = None) -> PartyData:
    """Parse 50a/59a party fields into name, BIC, account and address components."""
    options = options or []
    lines = _split_lines(value)
    party = PartyData(address_lines=[])
    if lines and lines[0].startswith("/"):
        party.account = _strip_account(lines[0])
        lines = lines[1:]
    if "F" in options:
        for line in lines:
            sub = PARTY_SUBFIELD_RE.match(line)
            if sub:
                number, text = sub.groups()
                if number == "1":
                    party.name = text.strip() or None
                else:
                    party.address_lines.append(text.strip())
            elif is_bic(line):
                party.bic = line
        return party
    if lines:
        if is_bic(lines[0]) and ("A" in options or not options):
            party.bic = lines[0]
        else:
            party.name = lines[0]
            party.address_lines = lines[1:]
    return party


@dataclass
class AgentData:
    bic: str | None = None
    name: str | None = None
    account: str | None = None
    address_lines: list[str] | None = None


def parse_agent(value: str, option: str | None = None) -> AgentData:
    """Parse a financial-institution field using its concrete option letter.

    Option A: BIC (with optional account line). Option D: name/address.
    Options B/C: account only. Without an option letter the value shape decides.
    """
    lines = _split_lines(value)
    account = _strip_account(lines[0]) if lines and lines[0].startswith("/") else None
    if option in ("B", "C"):
        return AgentData(account=account or (lines[0] if lines else None))
    if lines and is_bic(lines[0]):
        return AgentData(bic=lines[0], account=account)
    name = lines[0] if lines else None
    return AgentData(name=name, account=account, address_lines=lines[1:])


def account_choice(account: str | None) -> tuple[str, str]:
    """Return (element, value) for the AccountIdentification4Choice."""
    if account and is_iban(account):
        return "IBAN", account
    return "Othr", account or ""

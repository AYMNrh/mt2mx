from __future__ import annotations

import re
from dataclasses import dataclass, field

BLOCK4_RE = re.compile(r"\{4:(?P<body>.*?)(?:-\}|\})", re.DOTALL)
FIELD_RE = re.compile(r"^:(\d{2,3}[A-Z]?):", re.MULTILINE)
BIC_RE = re.compile(r"^[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?$")
IBAN_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")

COV_FIELD_MARKERS = ("50A", "50F", "50K", "50", "59A", "59F", "59", "70")

TYPE_MAP = {"103": "MT103", "202": "MT202", "910": "MT910", "920": "MT920"}


@dataclass
class MTPayload:
    sender_bic: str
    receiver_bic: str
    message_type: str
    input_output: str
    fields: list[tuple[str, str]] = field(default_factory=list)

    def get(self, tag: str) -> str | None:
        for current, value in self.fields:
            if self._matches_canonical(current, tag):
                return value
        return None

    def __getitem__(self, tag: str) -> str:
        value = self.get(tag)
        if value is None:
            raise KeyError(tag)
        return value

    def _matches_canonical(self, current: str, tag: str) -> bool:
        if current == tag:
            return True
        if tag.endswith("a"):
            # "50a" denotes the field family: any option letter (50, 50A, 50F, ...).
            return current[:2] == tag[:2]
        return current[:2] == tag[:2] and current[2:].lower() == tag[2:].lower()

    def get_all(self, tag: str) -> list[str]:
        return [value for current, value in self.fields if self._matches_canonical(current, tag)]


def _block(body: str, number: str) -> str | None:
    match = re.search(rf"\{{{number}:(?P<content>.*?)\}}", body, re.DOTALL)
    return match.group("content") if match else None


def _parse_block1(content: str) -> str:
    if len(content) < 15:
        raise ValueError(f"block 1 too short: {content!r}")
    # LT address is 12 chars (BIC8 + branch4); BICFI accepts 8 or 11.
    return content[3:15][:11]


def _parse_block2(content: str) -> tuple[str, str, str]:
    if len(content) < 16:
        raise ValueError(f"block 2 too short: {content!r}")
    indicator = content[0]
    message_type = content[1:4]
    receiver_bic = content[4:16][:11]
    return indicator, message_type, receiver_bic


def _parse_block4(content: str) -> list[tuple[str, str]]:
    matches = list(FIELD_RE.finditer(content))
    fields: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        value = content[match.end():end].strip().rstrip("-").strip()
        fields.append((match.group(1), value))
    return fields


def parse_message(text: str) -> MTPayload:
    """Parse a SWIFT MT payload into structured fields with block metadata."""
    block1 = _block(text, "1")
    block2 = _block(text, "2")
    block4 = BLOCK4_RE.search(text)
    if block4 is None:
        raise ValueError("message has no block 4")
    if block1 is None or block2 is None:
        raise ValueError("message requires blocks 1 and 2")

    sender_bic = _parse_block1(block1)
    indicator, raw_type, receiver_bic = _parse_block2(block2)
    if raw_type not in TYPE_MAP:
        raise ValueError(f"unsupported message type in block 2: {raw_type}")

    fields = _parse_block4(block4.group("body"))
    message_type = TYPE_MAP[raw_type]
    if raw_type == "202" and any(
        tag in COV_FIELD_MARKERS for tag, _ in fields
    ):
        message_type = "MT202_COV"
    return MTPayload(
        sender_bic=sender_bic,
        receiver_bic=receiver_bic,
        message_type=message_type,
        input_output=indicator,
        fields=fields,
    )


def is_bic(value: str) -> bool:
    return bool(BIC_RE.match(value))


def is_iban(value: str) -> bool:
    return bool(IBAN_RE.match(value))

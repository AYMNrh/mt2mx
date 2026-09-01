from __future__ import annotations

from typing import Any, Iterable

TAGS = {
    "MT103": {
        1: "20", 2: "13C", 3: "23B", 4: "23E", 5: "26T", 6: "32A",
        7: "33B", 8: "36", 9: "50a", 10: "51A", 11: "52a", 12: "53a",
        13: "54a", 14: "55a", 15: "56a", 16: "57a", 17: "59a", 18: "70",
        19: "71A", 20: "71F", 21: "71G", 22: "72", 23: "77B",
    },
    "MT202": {
        1: "20", 2: "21", 3: "13C", 4: "32A", 5: "52a", 6: "53a",
        7: "54a", 8: "56a", 9: "57a", 10: "58a", 11: "72",
    },
    "MT202_COV": {
        1: "20", 2: "21", 3: "13C", 4: "32A", 5: "52a", 6: "53a",
        7: "54a", 8: "56a", 9: "57a", 10: "58a", 11: "72", 12: "50a",
        13: "52a", 14: "56a", 15: "57a", 16: "59a", 17: "70", 18: "72",
        19: "33B",
    },
    "MT910": {
        1: "20", 2: "21", 3: "25a", 4: "13D", 5: "32A", 6: "50a",
        7: "52a", 8: "56a", 9: "72",
    },
    "MT920": {1: "20", 2: "12", 3: "25", 4: "34F", 5: "34F"},
}

TARGETS = {
    "MT103": "pacs.008.001.08",
    "MT202": "pacs.009.001.08",
    "MT202_COV": "pacs.009.001.08",
    "MT910": "camt.054.001.08",
    "MT920": "camt.060.001.05",
}

SOURCE_IDS = {
    "MT103": "SR_2025_MT103|MX_pacs_008_001_08",
    "MT202": "SR_2025_MT202|MX_pacs_009_001_08",
    "MT202_COV": "SR_2025_MT202_COV|MX_pacs_009_001_08|PMPG_COVER_GUIDANCE",
    "MT910": "SR_2025_MT910|MX_camt_054_001_08",
    "MT920": "SR_2025_MT920|MX_camt_060_001_05",
}

REVIEW = (
    "Base-standard semantic candidate only; validate against the applicable CBPR+ "
    "Usage Guideline and SWIFT Translation Library before implementation."
)


def _party_paths(prefix: str, account_prefix: str) -> list[str]:
    return [
        f"{prefix}/Nm",
        f"{prefix}/PstlAdr/AdrLine",
        f"{prefix}/Id/OrgId/AnyBIC",
        f"{account_prefix}/Id/IBAN",
        f"{account_prefix}/Id/Othr/Id",
    ]


def _choice_party_paths(prefix: str, account_prefix: str) -> list[str]:
    return [
        f"{prefix}/Pty/Nm",
        f"{prefix}/Pty/PstlAdr/AdrLine",
        f"{prefix}/Pty/Id/OrgId/AnyBIC",
        f"{account_prefix}/Id/IBAN",
        f"{account_prefix}/Id/Othr/Id",
    ]


def _agent_paths(prefix: str, account_prefix: str | None = None) -> list[str]:
    paths = [
        f"{prefix}/FinInstnId/BICFI",
        f"{prefix}/FinInstnId/ClrSysMmbId/MmbId",
        f"{prefix}/FinInstnId/Nm",
        f"{prefix}/FinInstnId/PstlAdr/AdrLine",
    ]
    if account_prefix:
        paths.extend(
            [f"{account_prefix}/Id/IBAN", f"{account_prefix}/Id/Othr/Id"]
        )
    return paths


def curated_rules() -> list[dict[str, Any]]:
    """Return the complete evidence-graded baseline rule set.

    These are candidates, not CBPR+ approval. Every source occurrence is explicitly
    covered and all target paths are validated by the build against the exact XSD.
    """
    rows: list[dict[str, Any]] = []

    def add(
        message: str,
        number: int,
        paths: str | Iterable[str] | None,
        action: str,
        transformation: str,
        grade: str = "C",
        option: str = "ANY",
        corroboration: str = "",
        review_reason: str = REVIEW,
    ) -> None:
        if paths is None:
            values = [""]
        elif isinstance(paths, str):
            values = [paths]
        else:
            values = list(paths)
        for path in values:
            rows.append(
                {
                    "mt_message": message,
                    "mt_occurrence_no": number,
                    "mt_tag": TAGS[message][number],
                    "mt_option": option,
                    "mx_message_id": TARGETS[message],
                    "mx_path": path,
                    "mapping_action": action,
                    "transformation": transformation,
                    "evidence_grade": grade,
                    "evidence_source_ids": SOURCE_IDS[message],
                    "corroboration": corroboration,
                    "validation_status": (
                        "DOCUMENTED_GAP" if action == "NO_DIRECT_EQUIVALENT"
                        else "REVIEW_REQUIRED_CBPR"
                    ),
                    "review_reason": review_reason,
                }
            )

    # MT103 -> pacs.008.001.08
    r8 = "Document/FIToFICstmrCdtTrf"
    tx8 = f"{r8}/CdtTrfTxInf"
    st8 = f"{r8}/GrpHdr/SttlmInf"
    add("MT103", 1, f"{tx8}/PmtId/InstrId", "DIRECT_CANDIDATE", "Copy sender reference; length/character validation required.", "B", corroboration="Apache-2.0 pacs008-loader-mt103 and MIT Mixar agree on InstrId.")
    add("MT103", 2, [f"{tx8}/SttlmTmReq/CLSTm", f"{tx8}/SttlmTmReq/TillTm", f"{tx8}/SttlmTmReq/FrTm", f"{tx8}/SttlmTmReq/RjctTm"], "CONDITIONAL_CANDIDATE", "Select target by 13C code; convert HHMM plus offset to ISO time under agreed timezone policy.", "C")
    add("MT103", 3, f"{tx8}/PmtTpInf/LclInstrm/Prtry", "CONDITIONAL_CANDIDATE", "Translate bank-operation code only where the usage guideline permits proprietary local instrument.", "C", corroboration="Open-source converter uses LclInstrm/Prtry; not authoritative.")
    add("MT103", 4, [f"{tx8}/InstrForCdtrAgt/Cd", f"{tx8}/InstrForCdtrAgt/InstrInf", f"{tx8}/InstrForNxtAgt/Cd", f"{tx8}/InstrForNxtAgt/InstrInf"], "CONDITIONAL_CANDIDATE", "Translate each 23E code and narrative using the official code-specific rule; one MT occurrence may fan out.", "D")
    add("MT103", 5, f"{tx8}/Purp/Prtry", "CONDITIONAL_CANDIDATE", "Carry transaction type as proprietary purpose only when bilateral/usage rules allow.", "D")
    add("MT103", 6, [f"{tx8}/IntrBkSttlmDt", f"{tx8}/IntrBkSttlmAmt", f"{tx8}/IntrBkSttlmAmt/@Ccy"], "TRANSFORM", "Split YYMMDD + currency + comma-decimal amount; expand year under SWIFT date rules.", "B", corroboration="Apache-2.0 pacs008-loader-mt103 and MIT Mixar corroborate amount/currency/date split.")
    add("MT103", 7, [f"{tx8}/InstdAmt", f"{tx8}/InstdAmt/@Ccy"], "TRANSFORM", "Split currency and instructed amount.", "B")
    add("MT103", 8, f"{tx8}/XchgRate", "TRANSFORM", "Convert SWIFT decimal comma to ISO decimal representation.", "B")
    add("MT103", 9, _party_paths(f"{tx8}/Dbtr", f"{tx8}/DbtrAcct"), "CONDITIONAL_CANDIDATE", "Parse option A/F/K into party identifier, name/address and account components; preserve unmapped source text for review.", "B", corroboration="Multiple open-source converters corroborate debtor and debtor-account semantics.")
    add("MT103", 10, None, "NO_DIRECT_EQUIVALENT", "Field 51A is network/sending-institution context; evaluate Business Application Header mapping rather than forcing it into the document.", "D", review_reason="Requires Business Application Header and CBPR+ rule review; this package inventories ISO Document paths only.")
    add("MT103", 11, _agent_paths(f"{tx8}/DbtrAgt", f"{tx8}/DbtrAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse option A/D into debtor-agent identifier, name/address and account.", "B")
    add("MT103", 12, _agent_paths(f"{st8}/InstgRmbrsmntAgt", f"{st8}/InstgRmbrsmntAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse sender's correspondent as instructing reimbursement agent/account when settlement method permits.", "B")
    add("MT103", 13, _agent_paths(f"{st8}/InstdRmbrsmntAgt", f"{st8}/InstdRmbrsmntAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse receiver's correspondent as instructed reimbursement agent/account when settlement method permits.", "B")
    add("MT103", 14, _agent_paths(f"{st8}/ThrdRmbrsmntAgt", f"{st8}/ThrdRmbrsmntAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse third reimbursement institution and account.", "B")
    add("MT103", 15, _agent_paths(f"{tx8}/IntrmyAgt1", f"{tx8}/IntrmyAgt1Acct"), "CONDITIONAL_CANDIDATE", "Parse intermediary option A/C/D into agent and account; option C requires account-only handling.", "B")
    add("MT103", 16, _agent_paths(f"{tx8}/CdtrAgt", f"{tx8}/CdtrAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse account-with institution as creditor agent/account.", "B", corroboration="Open-source converters corroborate creditor-agent semantics.")
    add("MT103", 17, _party_paths(f"{tx8}/Cdtr", f"{tx8}/CdtrAcct"), "CONDITIONAL_CANDIDATE", "Parse no-letter/A/F beneficiary into creditor party and account components.", "B", corroboration="Multiple open-source converters corroborate creditor and creditor-account semantics.")
    add("MT103", 18, f"{tx8}/RmtInf/Ustrd", "TRANSFORM", "Copy narrative with line joining and MX length/repetition controls; structured remittance requires separate parsing.", "B")
    add("MT103", 19, f"{tx8}/ChrgBr", "TRANSFORM", "Translate OUR→DEBT, BEN→CRED, SHA→SHAR; reject unknown code.", "B", corroboration="Apache-2.0 pacs008-loader-mt103 publishes the same code map.")
    add("MT103", 20, [f"{tx8}/ChrgsInf/Amt", f"{tx8}/ChrgsInf/Amt/@Ccy"], "TRANSFORM", "Split sender's charge currency/amount; charge-agent identity comes from message context, not 71F alone.", "B")
    add("MT103", 21, [f"{tx8}/ChrgsInf/Amt", f"{tx8}/ChrgsInf/Amt/@Ccy"], "TRANSFORM", "Split receiver's charge currency/amount; preserve charge role separately because ChrgsInf repeats.", "B")
    add("MT103", 22, f"{tx8}/InstrForNxtAgt/InstrInf", "CONDITIONAL_CANDIDATE", "Parse code lines; translate supported codes to structured instruction code and retain permitted narrative.", "C")
    add("MT103", 23, [f"{tx8}/RgltryRptg/DbtCdtRptgInd", f"{tx8}/RgltryRptg/Authrty/Ctry", f"{tx8}/RgltryRptg/Dtls/Inf"], "CONDITIONAL_CANDIDATE", "Parse debit/credit indicator, country and regulatory narrative where encoded; otherwise retain as review text.", "B")

    # Common MT202 / MT202 COV sequence-A -> pacs.009.001.08
    r9 = "Document/FICdtTrf"
    tx9 = f"{r9}/CdtTrfTxInf"
    st9 = f"{r9}/GrpHdr/SttlmInf"

    def add_fi_sequence(message: str) -> None:
        add(message, 1, f"{tx9}/PmtId/InstrId", "DIRECT_CANDIDATE", "Copy transaction reference as instruction identification subject to usage constraints.", "B", corroboration="MIT Mixar corroborates InstrId.")
        add(message, 2, f"{tx9}/PmtId/EndToEndId", "CONDITIONAL_CANDIDATE", "Carry related reference as end-to-end identification only under the official translation rule.", "C")
        add(message, 3, [f"{tx9}/SttlmTmReq/CLSTm", f"{tx9}/SttlmTmReq/TillTm", f"{tx9}/SttlmTmReq/FrTm", f"{tx9}/SttlmTmReq/RjctTm"], "CONDITIONAL_CANDIDATE", "Select target by 13C code and normalize time/offset.", "C")
        add(message, 4, [f"{tx9}/IntrBkSttlmDt", f"{tx9}/IntrBkSttlmAmt", f"{tx9}/IntrBkSttlmAmt/@Ccy"], "TRANSFORM", "Split value date, currency and amount.", "B", corroboration="MIT Mixar corroborates amount/currency/date split.")
        add(message, 5, _agent_paths(f"{tx9}/Dbtr", f"{tx9}/DbtrAcct"), "CONDITIONAL_CANDIDATE", "Parse ordering institution as debtor FI/account; sender fallback is outside this field-only rule.", "B")
        add(message, 6, _agent_paths(f"{st9}/InstgRmbrsmntAgt", f"{st9}/InstgRmbrsmntAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse sender's correspondent as instructing reimbursement agent/account.", "B")
        add(message, 7, _agent_paths(f"{st9}/InstdRmbrsmntAgt", f"{st9}/InstdRmbrsmntAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse receiver's correspondent as instructed reimbursement agent/account.", "B")
        add(message, 8, _agent_paths(f"{tx9}/IntrmyAgt1", f"{tx9}/IntrmyAgt1Acct"), "CONDITIONAL_CANDIDATE", "Parse intermediary institution and account.", "B")
        add(message, 9, _agent_paths(f"{tx9}/CdtrAgt", f"{tx9}/CdtrAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse account-with institution as creditor agent/account.", "B")
        add(message, 10, _agent_paths(f"{tx9}/Cdtr", f"{tx9}/CdtrAcct"), "CONDITIONAL_CANDIDATE", "Parse beneficiary institution as creditor FI/account.", "B")
        add(message, 11, f"{tx9}/InstrForNxtAgt/InstrInf", "CONDITIONAL_CANDIDATE", "Parse code lines and retain only permitted instruction narrative.", "C")

    add_fi_sequence("MT202")
    add_fi_sequence("MT202_COV")

    # MT202 COV sequence B -> underlying customer transfer in pacs.009.
    u = f"{tx9}/UndrlygCstmrCdtTrf"
    add("MT202_COV", 12, _party_paths(f"{u}/Dbtr", f"{u}/DbtrAcct"), "CONDITIONAL_CANDIDATE", "Parse ordering customer into underlying debtor and account.", "B")
    add("MT202_COV", 13, _agent_paths(f"{u}/DbtrAgt", f"{u}/DbtrAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse underlying ordering institution as debtor agent/account.", "B")
    add("MT202_COV", 14, _agent_paths(f"{u}/IntrmyAgt1", f"{u}/IntrmyAgt1Acct"), "CONDITIONAL_CANDIDATE", "Parse underlying intermediary institution and account.", "B")
    add("MT202_COV", 15, _agent_paths(f"{u}/CdtrAgt", f"{u}/CdtrAgtAcct"), "CONDITIONAL_CANDIDATE", "Parse underlying account-with institution as creditor agent/account.", "B")
    add("MT202_COV", 16, _party_paths(f"{u}/Cdtr", f"{u}/CdtrAcct"), "CONDITIONAL_CANDIDATE", "Parse beneficiary customer into underlying creditor and account.", "B")
    add("MT202_COV", 17, f"{u}/RmtInf/Ustrd", "TRANSFORM", "Copy permitted remittance narrative; structured remittance requires a separate rule.", "B")
    add("MT202_COV", 18, f"{u}/InstrForNxtAgt/InstrInf", "CONDITIONAL_CANDIDATE", "Parse underlying sender-to-receiver codes and permitted narrative.", "C")
    add("MT202_COV", 19, [f"{u}/InstdAmt", f"{u}/InstdAmt/@Ccy"], "TRANSFORM", "Split underlying instructed currency and amount.", "B")

    # MT910 -> camt.054.001.08
    c54 = "Document/BkToCstmrDbtCdtNtfctn"
    ntry = f"{c54}/Ntfctn/Ntry"
    txd = f"{ntry}/NtryDtls/TxDtls"
    refs = f"{txd}/Refs"
    parties = f"{txd}/RltdPties"
    agents = f"{txd}/RltdAgts"
    add("MT910", 1, [f"{ntry}/NtryRef", f"{refs}/AcctSvcrRef"], "CONDITIONAL_CANDIDATE", "Use as entry/account-servicer reference according to notification construction policy; do not duplicate without provenance.", "C")
    add("MT910", 2, [f"{refs}/InstrId", f"{refs}/EndToEndId", f"{refs}/TxId"], "CONDITIONAL_CANDIDATE", "Field 21 copies a reference from the causing payment; choose reference type from the originating message and retain provenance.", "D")
    add("MT910", 3, [f"{c54}/Ntfctn/Acct/Id/IBAN", f"{c54}/Ntfctn/Acct/Id/Othr/Id"], "CONDITIONAL_CANDIDATE", "Parse no-letter/P account identification; choose IBAN only after validation.", "B")
    add("MT910", 4, f"{ntry}/BookgDt/DtTm", "TRANSFORM", "Convert SWIFT date/time and UTC offset to ISO DateTime; local-time assumptions require policy.", "B")
    add("MT910", 5, [f"{ntry}/ValDt/Dt", f"{ntry}/Amt", f"{ntry}/Amt/@Ccy", f"{ntry}/CdtDbtInd"], "TRANSFORM", "Split value date/currency/amount; set credit/debit indicator to CRDT because MT910 confirms a credit.", "B")
    add("MT910", 6, _choice_party_paths(f"{parties}/Dbtr", f"{parties}/DbtrAcct"), "CONDITIONAL_CANDIDATE", "Parse ordering customer into related debtor party/account.", "B")
    add("MT910", 7, _agent_paths(f"{agents}/DbtrAgt"), "CONDITIONAL_CANDIDATE", "Parse ordering institution as related debtor agent.", "B")
    add("MT910", 8, _agent_paths(f"{agents}/IntrmyAgt1"), "CONDITIONAL_CANDIDATE", "Parse intermediary as related intermediary agent.", "B")
    add("MT910", 9, f"{txd}/AddtlTxInf", "CONDITIONAL_CANDIDATE", "Retain permitted sender-to-receiver narrative as additional transaction information after code review.", "C")

    # MT920 -> camt.060.001.05
    c60 = "Document/AcctRptgReq"
    req = f"{c60}/RptgReq"
    add("MT920", 1, f"{req}/Id", "DIRECT_CANDIDATE", "Copy request reference subject to MX length/character validation.", "B")
    add("MT920", 2, f"{req}/ReqdMsgNmId", "TRANSFORM", "Translate 940/950 to camt.053 and 941/942 to the agreed camt.052 reporting profile; exact message version is bilateral/usage-rule data.", "C")
    add("MT920", 3, [f"{req}/Acct/Id/IBAN", f"{req}/Acct/Id/Othr/Id"], "CONDITIONAL_CANDIDATE", "Choose IBAN only after validation; otherwise use Other/Id.", "B")
    add("MT920", 4, [f"{req}/ReqdTxTp/FlrLmt/Amt", f"{req}/ReqdTxTp/FlrLmt/Amt/@Ccy", f"{req}/ReqdTxTp/FlrLmt/CdtDbtInd"], "TRANSFORM", "Split floor-limit currency/amount and set DBIT for the debit limit; enforce MT920 C1/C2/C3.", "B")
    add("MT920", 5, [f"{req}/ReqdTxTp/FlrLmt/Amt", f"{req}/ReqdTxTp/FlrLmt/Amt/@Ccy", f"{req}/ReqdTxTp/FlrLmt/CdtDbtInd"], "TRANSFORM", "Split floor-limit currency/amount and set CRDT for the credit limit; enforce MT920 C1/C2/C3.", "B")

    return rows

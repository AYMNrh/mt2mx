# MT → MX translation review

Generated 2026-09-01T08:53:13+00:00 (UTC). Approval status: **REVIEW_REQUIRED_CBPR**.

## Summary

- Samples translated: **6**
- Schema-valid outputs: **6/6**
- Field-level rows: 65 (mapped 61, skipped 4, present-unmapped 0)

## Synthesized values (schema-mandated, not present in MT)

- camt.054 bank transaction code: 1
- camt.054 status: 1
- camt.060 account owner: 1
- camt.060 request status: 1
- header/agent fallback: 1

## Per-sample results

| Sample | MT | MX | Mapped | Skipped | Unmapped | XSD |
|---|---|---|---|---|---|---|
| mt103_basic | MT103 | pacs.008.001.08 | 9 | 1 | 0 | PASS |
| mt103_fx | MT103 | pacs.008.001.08 | 16 | 3 | 0 | PASS |
| mt202_basic | MT202 | pacs.009.001.08 | 9 | 0 | 0 | PASS |
| mt202cov_basic | MT202_COV | pacs.009.001.08 | 14 | 0 | 0 | PASS |
| mt910_basic | MT910 | camt.054.001.08 | 8 | 0 | 0 | PASS |
| mt920_basic | MT920 | camt.060.001.05 | 5 | 0 | 0 | PASS |

## Field dispositions

| Sample | Tag | Status | Detail |
|---|---|---|---|
| mt103_basic | :23B: | SKIPPED | bank operation code is profile-dependent; no safe direct element |
| mt103_basic | :32A: | MAPPED | CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt;GrpHdr/IntrBkSttlmDt |
| mt103_basic | :20: | MAPPED | GrpHdr/MsgId |
| mt103_basic | :20: | MAPPED | CdtTrfTxInf/PmtId/InstrId |
| mt103_basic | :71A: | MAPPED | CdtTrfTxInf/ChrgBr |
| mt103_basic | :50a: | MAPPED | CdtTrfTxInf/Dbtr;DbtrAcct |
| mt103_basic | :52a: | MAPPED | CdtTrfTxInf/DbtrAgt |
| mt103_basic | :57a: | MAPPED | CdtTrfTxInf/CdtrAgt |
| mt103_basic | :59a: | MAPPED | CdtTrfTxInf/Cdtr;CdtrAcct |
| mt103_basic | :70: | MAPPED | CdtTrfTxInf/RmtInf/Ustrd |
| mt103_fx | :71F: | SKIPPED | ChrgsInf requires Agt, which the MT field cannot supply (DQ-009); retained for review |
| mt103_fx | :71G: | SKIPPED | ChrgsInf requires Agt, which the MT field cannot supply (DQ-009); retained for review |
| mt103_fx | :23B: | SKIPPED | bank operation code is profile-dependent; no safe direct element |
| mt103_fx | :32A: | MAPPED | CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt;GrpHdr/IntrBkSttlmDt |
| mt103_fx | :20: | MAPPED | GrpHdr/MsgId |
| mt103_fx | :20: | MAPPED | CdtTrfTxInf/PmtId/InstrId |
| mt103_fx | :13C: | MAPPED | CdtTrfTxInf/SttlmTmReq/CLSTm |
| mt103_fx | :33B: | MAPPED | CdtTrfTxInf/InstdAmt+Ccy |
| mt103_fx | :36: | MAPPED | CdtTrfTxInf/XchgRate |
| mt103_fx | :71A: | MAPPED | CdtTrfTxInf/ChrgBr |
| mt103_fx | :50a: | MAPPED | CdtTrfTxInf/Dbtr;DbtrAcct |
| mt103_fx | :52a: | MAPPED | CdtTrfTxInf/DbtrAgt |
| mt103_fx | :57a: | MAPPED | CdtTrfTxInf/CdtrAgt |
| mt103_fx | :59a: | MAPPED | CdtTrfTxInf/Cdtr;CdtrAcct |
| mt103_fx | :23E: | MAPPED | CdtTrfTxInf/InstrForCdtrAgt |
| mt103_fx | :72: | MAPPED | CdtTrfTxInf/InstrForNxtAgt/InstrInf |
| mt103_fx | :26T: | MAPPED | CdtTrfTxInf/Purp/Prtry |
| mt103_fx | :77B: | MAPPED | CdtTrfTxInf/RgltryRptg/Dtls/Inf |
| mt103_fx | :70: | MAPPED | CdtTrfTxInf/RmtInf/Ustrd |
| mt202_basic | :32A: | MAPPED | CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt |
| mt202_basic | :20: | MAPPED | GrpHdr/MsgId |
| mt202_basic | :20: | MAPPED | CdtTrfTxInf/PmtId/InstrId |
| mt202_basic | :21: | MAPPED | CdtTrfTxInf/PmtId/EndToEndId |
| mt202_basic | :56a: | MAPPED | CdtTrfTxInf/IntrmyAgt1 |
| mt202_basic | :52a: | MAPPED | CdtTrfTxInf/Dbtr |
| mt202_basic | :57a: | MAPPED | CdtTrfTxInf/CdtrAgt |
| mt202_basic | :58a: | MAPPED | CdtTrfTxInf/Cdtr |
| mt202_basic | :53a: | MAPPED | GrpHdr/SttlmInf/InstgRmbrsmntAgt |
| mt202cov_basic | :32A: | MAPPED | CdtTrfTxInf/IntrBkSttlmAmt+Ccy;IntrBkSttlmDt |
| mt202cov_basic | :20: | MAPPED | GrpHdr/MsgId |
| mt202cov_basic | :20: | MAPPED | CdtTrfTxInf/PmtId/InstrId |
| mt202cov_basic | :21: | MAPPED | CdtTrfTxInf/PmtId/EndToEndId |
| mt202cov_basic | :52a: | MAPPED | CdtTrfTxInf/Dbtr |
| mt202cov_basic | :57a: | MAPPED | CdtTrfTxInf/CdtrAgt |
| mt202cov_basic | :58a: | MAPPED | CdtTrfTxInf/Cdtr |
| mt202cov_basic | :50a: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/Dbtr;DbtrAcct |
| mt202cov_basic | :52a: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/DbtrAgt |
| mt202cov_basic | :57a: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/CdtrAgt |
| mt202cov_basic | :59a: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/Cdtr;CdtrAcct |
| mt202cov_basic | :72: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/InstrForNxtAgt/InstrInf |
| mt202cov_basic | :70: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/RmtInf/Ustrd |
| mt202cov_basic | :33B: | MAPPED | CdtTrfTxInf/UndrlygCstmrCdtTrf/InstdAmt+Ccy |
| mt910_basic | :32A: | MAPPED | Ntry/Amt+Ccy;Ntry/ValDt/Dt |
| mt910_basic | :20: | MAPPED | GrpHdr/MsgId |
| mt910_basic | :25a: | MAPPED | Ntfctn/Acct/Id |
| mt910_basic | :13D: | MAPPED | Ntry/BookgDt/DtTm |
| mt910_basic | :21: | MAPPED | Ntry/NtryDtls/TxDtls/Refs/EndToEndId |
| mt910_basic | :50a: | MAPPED | Ntry/NtryDtls/TxDtls/RltdPties/Dbtr;DbtrAcct |
| mt910_basic | :52a: | MAPPED | Ntry/NtryDtls/TxDtls/RltdAgts/DbtrAgt |
| mt910_basic | :72: | MAPPED | Ntry/NtryDtls/TxDtls/AddtlTxInf |
| mt920_basic | :20: | MAPPED | GrpHdr/MsgId;RptgReq/Id |
| mt920_basic | :12: | MAPPED | RptgReq/ReqdMsgNmId |
| mt920_basic | :25: | MAPPED | RptgReq/Acct/Id |
| mt920_basic | :34F: | MAPPED | RptgReq/ReqdTxTp/FlrLmt (#1) |
| mt920_basic | :34F: | MAPPED | RptgReq/ReqdTxTp/FlrLmt (#2) |
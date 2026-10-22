# 01 - Bank reconciliation (statement x ledger)

**Problem:** every day the treasury must prove that what the bank says happened (statement)
is exactly what accounting booked (general ledger). Any difference is a *break* that must be
explained before the books close.

**What this does:** generates a synthetic statement and ledger, matches them by `doc_id`
and classifies each entry:

| Status | Meaning | Real-world example |
|---|---|---|
| `MATCHED` | Same document, same amount | TED booked correctly |
| `AMOUNT_MISMATCH` | Same document, different amount | Typo: 118,182.06 booked as 118,128.06 |
| `STATEMENT_ONLY` | At the bank, missing in the ledger | Monthly bank fee nobody booked |
| `LEDGER_ONLY` | In the ledger, never settled | Manual entry for a TED that never happened |
| `DUPLICATE` | Same document twice on one side | Entry booked twice |

## Run

```bash
cd 01-conciliacao-extrato
python3 scripts/generate_data.py
python3 src/reconcile.py
python3 src/reconcile.py --fail-on-break   # exit code 1 when there are breaks
```

Money is always handled with `Decimal`, never `float`.

## Roadmap

- [x] Day 1: data generator + reconciliation script, first pull request
- [ ] Day 2: unit tests with pytest
- [ ] Day 3: ruff + pre-commit
- [ ] Day 4: GitHub Actions CI on every pull request + branch protection

"""Generate SYNTHETIC bank statement and general ledger files for reconciliation.

All data is fictional and generated from a fixed seed, so every run produces
exactly the same files. No real bank, client or amount is used.

Planted breaks (so we know the expected answer):
  - 1 amount mismatch     (typo in the ledger: digits swapped)
  - 1 statement-only item (bank fee nobody booked in the ledger)
  - 1 ledger-only item    (manual entry that never settled at the bank)
  - 1 duplicate in ledger (same document booked twice)

Usage:
    python3 scripts/generate_data.py            # writes data/statement.csv and data/ledger.csv
    python3 scripts/generate_data.py --rows 60  # more transactions
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

SEED = 42
FIELDS = ["date", "doc_id", "description", "amount"]

# (description, min, max, sign) -> sign +1 = cash in, -1 = cash out
TRANSACTION_TYPES = [
    ("TED received - client deposit", 5_000, 250_000, 1),
    ("PIX received - client deposit", 100, 50_000, 1),
    ("PIX sent - client withdrawal", 100, 40_000, -1),
    ("LFT purchase - Selic settlement", 500_000, 5_000_000, -1),
    ("LTN maturity - Selic settlement", 500_000, 3_000_000, 1),
    ("CDB redemption - client", 1_000, 200_000, -1),
    ("FX settlement - USD sale", 50_000, 800_000, 1),
    ("FX settlement - USD purchase", 50_000, 800_000, -1),
]


def money(value: float) -> Decimal:
    """Always use Decimal for money. float(0.1 + 0.2) != 0.3 breaks reconciliations."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def business_days(start: date, n: int) -> list[date]:
    days, current = [], start
    while len(days) < n:
        if current.weekday() < 5:  # Mon-Fri (holidays ignored on day 1)
            days.append(current)
        current += timedelta(days=1)
    return days


def build_transactions(rows: int, rng: random.Random) -> list[dict]:
    days = business_days(date(2026, 10, 1), 15)
    transactions = []
    for i in range(1, rows + 1):
        desc, low, high, sign = rng.choice(TRANSACTION_TYPES)
        amount = money(rng.uniform(low, high)) * sign
        transactions.append(
            {
                "date": rng.choice(days).isoformat(),
                "doc_id": f"DOC{i:05d}",
                "description": desc,
                "amount": f"{amount:.2f}",
            }
        )
    transactions.sort(key=lambda t: (t["date"], t["doc_id"]))
    return transactions


def plant_breaks(statement: list[dict]) -> tuple[list[dict], list[dict]]:
    ledger = [dict(t) for t in statement]

    # 1) Amount mismatch: swap the last two digits before the decimal point (typo)
    target = ledger[3]
    integer, cents = target["amount"].split(".")
    target["amount"] = f"{integer[:-2]}{integer[-1]}{integer[-2]}.{cents}"
    if target["amount"] == statement[3]["amount"]:  # digits were equal, force a change
        target["amount"] = f"{Decimal(target['amount']) + Decimal('9.00'):.2f}"

    # 2) Statement-only: bank fee not booked in the ledger
    statement.append(
        {"date": statement[-1]["date"], "doc_id": "FEE00001",
         "description": "Bank fee - monthly package", "amount": "-89.90"}
    )

    # 3) Ledger-only: manual entry that never settled
    ledger.append(
        {"date": statement[-1]["date"], "doc_id": "MAN00001",
         "description": "Manual entry - pending TED", "amount": "15000.00"}
    )

    # 4) Duplicate in ledger
    ledger.append(dict(ledger[7]))

    return statement, ledger


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()

    rng = random.Random(SEED)
    statement = build_transactions(args.rows, rng)
    statement, ledger = plant_breaks(statement)

    write_csv(args.out / "statement.csv", statement)
    write_csv(args.out / "ledger.csv", ledger)
    print(f"statement.csv: {len(statement)} rows | ledger.csv: {len(ledger)} rows -> {args.out}")


if __name__ == "__main__":
    main()

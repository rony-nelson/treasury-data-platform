"""Bank statement x general ledger reconciliation (SYNTHETIC data only).

Matches entries by doc_id and classifies each one as:
  MATCHED          same doc_id and same amount on both sides
  AMOUNT_MISMATCH  same doc_id, different amount
  STATEMENT_ONLY   at the bank, missing in the ledger (ex.: unbooked fee)
  LEDGER_ONLY      in the ledger, never settled at the bank
  DUPLICATE        doc_id appears more than once on the same side

Usage:
    python3 src/reconcile.py
    python3 src/reconcile.py --fail-on-break   # exit code 1 if any break (useful in CI)
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = Decimal(row["amount"])  # never float for money
    return rows


def reconcile(statement: list[dict], ledger: list[dict]) -> list[dict]:
    results: list[dict] = []

    for side, rows in (("statement", statement), ("ledger", ledger)):
        counts = Counter(r["doc_id"] for r in rows)
        for doc_id, n in counts.items():
            if n > 1:
                results.append({"doc_id": doc_id, "status": "DUPLICATE",
                                "statement_amount": "", "ledger_amount": "",
                                "difference": "", "note": f"{n}x in {side}"})

    stmt = {r["doc_id"]: r for r in statement}
    ledg = {r["doc_id"]: r for r in ledger}

    for doc_id in sorted(stmt.keys() | ledg.keys()):
        s, g = stmt.get(doc_id), ledg.get(doc_id)
        if s and g:
            diff = s["amount"] - g["amount"]
            status = "MATCHED" if diff == 0 else "AMOUNT_MISMATCH"
            results.append({"doc_id": doc_id, "status": status,
                            "statement_amount": s["amount"], "ledger_amount": g["amount"],
                            "difference": diff, "note": s["description"]})
        elif s:
            results.append({"doc_id": doc_id, "status": "STATEMENT_ONLY",
                            "statement_amount": s["amount"], "ledger_amount": "",
                            "difference": s["amount"], "note": s["description"]})
        else:
            results.append({"doc_id": doc_id, "status": "LEDGER_ONLY",
                            "statement_amount": "", "ledger_amount": g["amount"],
                            "difference": -g["amount"], "note": g["description"]})
    return results


def summarize(results: list[dict]) -> Counter:
    return Counter(r["status"] for r in results)


def write_report(path: Path, results: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["doc_id", "status", "statement_amount", "ledger_amount", "difference", "note"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Statement x ledger reconciliation")
    parser.add_argument("--statement", type=Path, default=BASE / "data" / "statement.csv")
    parser.add_argument("--ledger", type=Path, default=BASE / "data" / "ledger.csv")
    parser.add_argument("--report", type=Path, default=BASE / "output" / "reconciliation_report.csv")
    parser.add_argument("--fail-on-break", action="store_true")
    args = parser.parse_args()

    results = reconcile(load(args.statement), load(args.ledger))
    write_report(args.report, results)

    summary = summarize(results)
    breaks = sum(n for status, n in summary.items() if status != "MATCHED")
    print("Reconciliation summary")
    for status in ("MATCHED", "AMOUNT_MISMATCH", "STATEMENT_ONLY", "LEDGER_ONLY", "DUPLICATE"):
        print(f"  {status:<16} {summary.get(status, 0):>4}")
    print(f"  {'BREAKS':<16} {breaks:>4}")
    print(f"Report: {args.report}")

    return 1 if (args.fail_on_break and breaks) else 0


if __name__ == "__main__":
    sys.exit(main())

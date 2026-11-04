"""Tests for the statement x ledger reconciliation (synthetic data only)."""

from __future__ import annotations

from decimal import Decimal

from reconcile import load, reconcile, summarize

# ---------- unit tests: small, hand-made inputs ----------


def test_same_doc_same_amount_is_matched(make_row):
    results = reconcile([make_row("DOC1", "100.00")], [make_row("DOC1", "100.00")])
    assert [r["status"] for r in results] == ["MATCHED"]


def test_same_doc_different_amount_is_mismatch(make_row):
    results = reconcile([make_row("DOC1", "100.00")], [make_row("DOC1", "46.00")])
    assert results[0]["status"] == "AMOUNT_MISMATCH"
    assert results[0]["difference"] == Decimal("54.00")


def test_only_at_the_bank_is_statement_only(make_row):
    results = reconcile([make_row("FEE1", "-89.90")], [])
    assert results[0]["status"] == "STATEMENT_ONLY"


def test_only_in_the_books_is_ledger_only(make_row):
    results = reconcile([], [make_row("MAN1", "15000.00")])
    assert results[0]["status"] == "LEDGER_ONLY"


def test_duplicate_is_never_also_matched(make_row):
    """Regression test for the DOC00035 bug: a duplicated document must be a break,
    never counted as MATCHED at the same time."""
    statement = [make_row("DOC1", "100.00")]
    ledger = [make_row("DOC1", "100.00"), make_row("DOC1", "100.00")]
    statuses = [r["status"] for r in reconcile(statement, ledger)]
    assert statuses == ["DUPLICATE"]


# ---------- end-to-end: the real generator, seed 42 ----------


def test_load_reads_money_as_decimal(synthetic_files):
    statement, _ = synthetic_files
    rows = load(statement)
    assert all(isinstance(r["amount"], Decimal) for r in rows)


def test_end_to_end_finds_the_4_planted_breaks(synthetic_files):
    statement, ledger = synthetic_files
    summary = summarize(reconcile(load(statement), load(ledger)))
    assert summary["AMOUNT_MISMATCH"] == 1
    assert summary["STATEMENT_ONLY"] == 1
    assert summary["LEDGER_ONLY"] == 1
    assert summary["DUPLICATE"] == 1


def test_end_to_end_matched_count(synthetic_files):
    """40 documents: 1 mismatch + 1 duplicate are breaks -> 38 MATCHED."""
    statement, ledger = synthetic_files
    summary = summarize(reconcile(load(statement), load(ledger)))
    assert summary["MATCHED"] == 38

"""Shared test fixtures (pytest loads this file automatically)."""

from __future__ import annotations

import sys
from decimal import Decimal

import generate_data
import pytest


@pytest.fixture
def make_row():
    """Build one statement/ledger row in a single line: make_row("DOC1", "100.00")."""

    def _make(doc_id: str, amount: str, description: str = "test entry") -> dict:
        return {
            "date": "2026-10-01",
            "doc_id": doc_id,
            "description": description,
            "amount": Decimal(amount),
        }

    return _make


@pytest.fixture
def synthetic_files(tmp_path, monkeypatch):
    """Run the REAL generator (seed 42) into a temporary folder and return its paths.

    tmp_path is deleted by pytest after the test, so nothing touches data/.
    """
    out = tmp_path / "data"
    monkeypatch.setattr(sys, "argv", ["generate_data.py", "--out", str(out)])
    generate_data.main()
    return out / "statement.csv", out / "ledger.csv"

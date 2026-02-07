from __future__ import annotations

from pathlib import Path

import pytest

from extractor.banks.wells_fargo import extract


SAMPLE_PDF = Path(__file__).resolve().parents[1] / "samples" / "wells_fargo_sample.pdf"


def _money_close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


def _reconcile_account(account) -> None:
    """
    Validación mínima “bancaria”:
    - Ningún balance debe ser None
    - Último balance coincide con balance final
    - begin_balance + sum(amounts) == end_balance
      (begin_balance lo inferimos con first_balance - first_amount)
    """
    txs = account.transactions
    assert txs, "La cuenta no tiene transacciones"

    # 1) balances completos
    assert all(t.balance is not None for t in txs), "Hay balances None en transacciones"

    # 2) amounts no cero (si el PDF tuviera un 0 real, ajusta este assert)
    assert all(t.amount != 0 for t in txs), "Hay montos 0.0 inesperados"

    # 3) reconciliación
    first = txs[0]
    last = txs[-1]

    begin_balance = float(first.balance) - float(first.amount)
    total_amounts = round(sum(float(t.amount) for t in txs), 2)
    expected_end = round(begin_balance + total_amounts, 2)
    end_balance = round(float(last.balance), 2)

    assert _money_close(expected_end, end_balance), (
        f"Reconciliación falló: begin={begin_balance} sum={total_amounts} "
        f"expected_end={expected_end} end={end_balance}"
    )

    # 4) sanity: fechas con formato ISO YYYY-MM-DD
    assert all(len(t.date) == 10 and t.date[4] == "-" and t.date[7] == "-" for t in txs), "Formato de fecha inválido"


def test_wells_fargo_sample_extract_structure_and_integrity():
    assert SAMPLE_PDF.exists(), f"No existe el sample PDF: {SAMPLE_PDF}"

    result = extract(str(SAMPLE_PDF))

    # Banco / año
    assert result.bank == "Wells Fargo"
    assert result.statement_year == 2024

    # Cuentas esperadas
    names = [a.name for a in result.accounts]
    assert set(names) == {"Checking", "Savings"}, f"Cuentas detectadas inesperadas: {names}"

    # Conteos esperados por el sample
    by_name = {a.name: a for a in result.accounts}
    assert len(by_name["Checking"].transactions) == 16
    assert len(by_name["Savings"].transactions) == 1
    assert sum(len(a.transactions) for a in result.accounts) == 17

    # Validación “bancaria” por cuenta
    _reconcile_account(by_name["Checking"])
    _reconcile_account(by_name["Savings"])

    # Sanity de signos en casos obvios del sample
    checking_txs = by_name["Checking"].transactions
    # Debe existir un eDeposit positivo
    assert any(("edeposit" in t.description.lower()) and (t.amount > 0) for t in checking_txs)
    # Debe existir un Purchase negativo
    assert any(("purchase" in t.description.lower()) and (t.amount < 0) for t in checking_txs)
    # Debe existir un "Zelle to" negativo
    assert any(("zelle to" in t.description.lower()) and (t.amount < 0) for t in checking_txs)
    # Debe existir un "Zelle From" positivo
    assert any(("zelle from" in t.description.lower()) and (t.amount > 0) for t in checking_txs)


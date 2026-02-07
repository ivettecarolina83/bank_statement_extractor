from __future__ import annotations

from typing import List

from .models import Transaction


def apply_sign_heuristics(transactions: List[Transaction]) -> List[Transaction]:
    """
    Heurística mínima mejorada (prioridad correcta):
    - Primero marcamos INFLOW si hay señales claras (deposit, zelle from, etc.)
    - Luego marcamos OUTFLOW (purchase, zelle to, fee, etc.)
    """
    inflow = (
        "deposit",
        "edeposit",
        "zelle from",
        "refund",
        "interest",
        "credit",
    )
    outflow = (
        "purchase",
        "payment",
        "zelle to",
        "withdrawal",
        "fee",
        "debit",
        "pos",
        "transfer debit",
    )

    out: List[Transaction] = []
    for t in transactions:
        d = t.description.lower()

        # 1) inflow primero (esto corrige eDeposit)
        if any(k in d for k in inflow):
            t.amount = abs(t.amount)
        # 2) outflow después
        elif any(k in d for k in outflow):
            t.amount = -abs(t.amount)

        out.append(t)

    return out

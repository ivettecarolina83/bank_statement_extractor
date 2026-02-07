from __future__ import annotations

from ..detect import detect_pdf
from ..models import Account, ExtractionResult
from ..segment import segment_transaction_history
from ..parse import parse_transactions_from_lines
from ..normalize import apply_sign_heuristics


def _forward_fill_balances(txs):
    """
    Rellena balances faltantes usando el último balance conocido dentro del mismo account.
    """
    last = None
    for t in txs:
        if t.balance is None:
            t.balance = last
        else:
            last = t.balance
    return txs


def extract(pdf_path: str) -> ExtractionResult:
    info = detect_pdf(pdf_path)

    sections = segment_transaction_history(pdf_path)

    accounts: list[Account] = []

    for s in sections:
        # Normalizar header
        raw = (s.header_line or "").strip().lower()

        # Si la "header_line" es realmente el encabezado de columnas, no es nombre de cuenta
        if "date" in raw and "description" in raw:
            # Buscar en el contexto cercano el nombre real del account
            ctx = " ".join(s.context_lines or []).lower()
            if "savings" in ctx:
                account_name = "Savings"
            elif "checking" in ctx:
                account_name = "Checking"
            else:
                account_name = "Checking"
        else:
            # En caso de que venga bien (p.ej. "Checking" / "Savings")
            account_name = (s.header_line or "Checking").strip()

        # Parsear transacciones del section
        txs = parse_transactions_from_lines(s.lines, info.statement_year)

        # Signos (+/-)
        txs = apply_sign_heuristics(txs)

        # Completar balances faltantes
        txs = _forward_fill_balances(txs)

        accounts.append(
            Account(
                name=account_name,
                currency="USD",
                transactions=txs,
            )
        )

    return ExtractionResult(
        bank="Wells Fargo",
        statement_year=info.statement_year,
        accounts=accounts,
    )

from __future__ import annotations

import re
import datetime
from typing import List, Optional

from .models import Transaction


DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})\b")


def _parse_money_candidates(line: str) -> List[float]:
    # Captura montos tipo 1,234.56
    money_re = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})*(?:\.\d{2}))")
    vals = []
    for m in money_re.findall(line):
        vals.append(float(m.replace(",", "")))
    return vals


def _clean_desc(first_line: str) -> str:
    # quitar fecha al inicio
    s = re.sub(r"^\d{1,2}/\d{1,2}\s*", "", first_line).strip()
    # quitar hasta dos montos al final (amount y balance típicamente)
    s = re.sub(
        r"\s+\d{1,3}(?:,\d{3})*(?:\.\d{2})(?:\s+\d{1,3}(?:,\d{3})*(?:\.\d{2}))?\s*$",
        "",
        s,
    ).strip()
    return s


def parse_transactions_from_lines(lines: List[str], statement_year: Optional[int]) -> List[Transaction]:
    """
    Parser stateful:
    - Una transacción inicia con una línea que comienza con fecha M/D
    - Las líneas siguientes (sin fecha) se agregan a la descripción
    - El monto y balance suelen venir al final de la primera línea (Wells Fargo)
    """
    year = statement_year or datetime.date.today().year

    blocks: List[List[str]] = []
    current: List[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if DATE_RE.match(line):
            if current:
                blocks.append(current)
            current = [line]
        else:
            if current:
                current.append(line)

    if current:
        blocks.append(current)

        txs: List[Transaction] = []
    last_balance: Optional[float] = None

    for block in blocks:
        first = block[0]
        dm = DATE_RE.match(first)
        if not dm:
            continue

        mm = int(dm.group(1))
        dd = int(dm.group(2))
        try:
            dt = datetime.date(year, mm, dd).isoformat()
        except ValueError:
            continue

        nums = _parse_money_candidates(first)
        raw_amount = None
        balance = None

        # Heurística Wells Fargo: si hay 2+ montos al final => (amount, balance)
        if len(nums) >= 2:
            raw_amount = nums[-2]
            balance = nums[-1]
        elif len(nums) == 1:
            raw_amount = nums[0]

        if raw_amount is None:
            continue

        desc_first = _clean_desc(first)
        desc_rest = " ".join(x.strip() for x in block[1:])
        description = (desc_first + " " + desc_rest).strip() if desc_rest else desc_first

        # fallback: si no viene balance, usar el último conocido
        if balance is None and last_balance is not None:
            balance = last_balance

        
        txs.append(Transaction(date=dt, description=description, amount=float(raw_amount), balance=balance))

    return txs

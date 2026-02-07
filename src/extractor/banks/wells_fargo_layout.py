from __future__ import annotations

import datetime
import re
from typing import Dict, List, Optional

import pdfplumber

from ..models import Transaction


DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")


def _to_float_money(s: str) -> Optional[float]:
    s = (s or "").strip().replace(",", "")
    if not s:
        return None
    # Wells Fargo en este PDF usa 25.46, 1,040.00, etc.
    if not re.fullmatch(r"\d+(?:\.\d{2})", s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _group_words_by_line(words: List[Dict], y_tol: float = 2.0) -> List[List[Dict]]:
    """
    Agrupa palabras por línea usando coordenada 'top' con tolerancia.
    """
    if not words:
        return []

    # ordenar por top y luego x0
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines: List[List[Dict]] = []
    current: List[Dict] = [words[0]]
    current_y = words[0]["top"]

    for w in words[1:]:
        if abs(w["top"] - current_y) <= y_tol:
            current.append(w)
        else:
            lines.append(sorted(current, key=lambda z: z["x0"]))
            current = [w]
            current_y = w["top"]

    lines.append(sorted(current, key=lambda z: z["x0"]))
    return lines


def extract_transactions_layout(
    pdf_path: str,
    page_indexes: List[int],
    statement_year: Optional[int],
) -> List[Transaction]:
    """
    Extrae transacciones por columnas (layout) usando coordenadas X.
    - amount se decide por columna: Additions => + , Subtractions => -
    - balance solo si aparece en columna Balance
    """
    year = statement_year or datetime.date.today().year

    # Rangos X basados en tu debug (page width 612)
    X_DATE_MAX = 100
    X_DESC_MIN, X_DESC_MAX = 100, 400
    X_ADD_MIN, X_ADD_MAX = 400, 455
    X_SUB_MIN, X_SUB_MAX = 455, 525
    X_BAL_MIN = 525

    txs: List[Transaction] = []

    with pdfplumber.open(pdf_path) as pdf:
        for pi in page_indexes:
            page = pdf.pages[pi]
            words = page.extract_words()

            # localizar la cabecera "Date ... balance" para definir región vertical
            header_tops = [w["top"] for w in words if w["text"] == "Date" and w["x0"] < 120]
            start_y = min(header_tops) + 6 if header_tops else 0

            # (CORREGIDO) indentación del ending_candidates
            ending_candidates = [
                w["top"]
                for w in words
                if w["text"] == "Ending" and w["x0"] < 120 and w["top"] > start_y
            ]
            end_y = min(ending_candidates) - 2 if ending_candidates else page.height

            # solo palabras dentro del área de la tabla
            table_words = [w for w in words if (w["top"] >= start_y and w["top"] <= end_y)]

            # agrupar por línea
            lines = _group_words_by_line(table_words, y_tol=2.0)

            current_date: Optional[str] = None
            current_desc_parts: List[str] = []
            current_amount: Optional[float] = None
            current_balance: Optional[float] = None

            def flush_current():
                nonlocal current_date, current_desc_parts, current_amount, current_balance
                if current_date and current_amount is not None:
                    desc = " ".join(p.strip() for p in current_desc_parts if p.strip()).strip()
                    txs.append(
                        Transaction(
                            date=current_date,
                            description=desc,
                            amount=float(current_amount),
                            balance=current_balance,
                        )
                    )
                current_date = None
                current_desc_parts = []
                current_amount = None
                current_balance = None

            for line_words in lines:
                # separar palabras por columnas
                date_tokens = [w["text"] for w in line_words if w["x0"] < X_DATE_MAX]
                desc_tokens = [w["text"] for w in line_words if X_DESC_MIN <= w["x0"] < X_DESC_MAX]
                add_tokens = [w["text"] for w in line_words if X_ADD_MIN <= w["x0"] < X_ADD_MAX]
                sub_tokens = [w["text"] for w in line_words if X_SUB_MIN <= w["x0"] < X_SUB_MAX]
                bal_tokens = [w["text"] for w in line_words if w["x0"] >= X_BAL_MIN]

                # ¿Esta línea inicia transacción?
                date_str = date_tokens[0] if date_tokens else ""
                dm = DATE_RE.match(date_str)

                if dm:
                    # nueva transacción => flush anterior
                    flush_current()

                    mm = int(dm.group(1))
                    dd = int(dm.group(2))
                    try:
                        current_date = datetime.date(year, mm, dd).isoformat()
                    except ValueError:
                        current_date = None

                    current_desc_parts = []
                    if desc_tokens:
                        current_desc_parts.append(" ".join(desc_tokens))

                    add_val = _to_float_money(add_tokens[-1]) if add_tokens else None
                    sub_val = _to_float_money(sub_tokens[-1]) if sub_tokens else None
                    bal_val = _to_float_money(bal_tokens[-1]) if bal_tokens else None

                    # amount por columna
                    if add_val is not None:
                        current_amount = +add_val
                    elif sub_val is not None:
                        current_amount = -sub_val
                    else:
                        current_amount = None

                    current_balance = bal_val

                else:
                    # continuación de descripción (líneas como "Duluth GA 1230", etc.)
                    if current_date and desc_tokens:
                        current_desc_parts.append(" ".join(desc_tokens))

            # flush final de la página
            flush_current()

    # (NUEVO) Fill-down de balance: Wells Fargo no imprime balance en cada fila
    last_balance: Optional[float] = None
    for t in txs:
        if t.balance is not None:
            last_balance = t.balance
        elif last_balance is not None:
            t.balance = last_balance

    return txs

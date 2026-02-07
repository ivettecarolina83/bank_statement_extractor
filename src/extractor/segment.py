from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pdfplumber


@dataclass
class TableSection:
    page_index: int
    context_lines: List[str]        # líneas previas para inferir tipo de cuenta
    header_line: Optional[str]
    lines: List[str]                # líneas dentro de la tabla (sin header)


def _find_section_block(lines: List[str]) -> Optional[Tuple[int, int, Optional[str]]]:
    """
    Encuentra un bloque de 'Transaction history' en una página:
    - inicio: después del header de columnas (línea que comienza con 'Date')
    - fin: antes de 'Totals' o 'Ending balance on'
    """
    if "Transaction history" not in lines:
        return None

    start = None
    header = None

    th_idx = lines.index("Transaction history")

    for i in range(th_idx + 1, len(lines)):
        if lines[i].startswith("Date"):
            header = lines[i]
            start = i + 1
            break

    if start is None:
        return None

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("Totals") or lines[i].startswith("Ending balance on"):
            end = i
            break

    return start, end, header


def segment_transaction_history(pdf_path: str) -> List[TableSection]:
    """
    Extrae secciones de tabla para 'Transaction history' por página.
    En Wells Fargo, puede continuar en varias páginas; lo manejaremos después en el driver.
    """
    sections: List[TableSection] = []

    with pdfplumber.open(pdf_path) as pdf:
        for pidx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.splitlines()
            found = _find_section_block(lines)
            if not found:
                continue

            start, end, header = found
            context_start = max(0, start - 40)
            context = lines[context_start:start]

            section_lines = lines[start:end]
            sections.append(
                TableSection(
                    page_index=pidx,
                    context_lines=context,
                    header_line=header,
                    lines=section_lines,
                )
            )

    return sections

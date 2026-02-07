from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import pdfplumber


@dataclass(frozen=True)
class DocumentInfo:
    is_pdf: bool
    is_digital_pdf: bool
    pages: int
    statement_year: Optional[int]


_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def detect_pdf(pdf_path: str) -> DocumentInfo:
    """
    Determina si el PDF tiene texto extraíble (digital) y trata de inferir el año del statement.
    """
    with pdfplumber.open(pdf_path) as pdf:
        pages = len(pdf.pages)
        text_sample = ""
        for i in range(min(3, pages)):
            t = pdf.pages[i].extract_text() or ""
            text_sample += "\n" + t

        # Heurística digital: hay texto suficiente
        is_digital = len(text_sample.strip()) > 200

        # Inferir año: buscar 20xx cerca de "Statement period" si existe
        year = None
        if "Statement period" in text_sample:
            idx = text_sample.find("Statement period")
            window = text_sample[idx : idx + 500]
            m = _YEAR_RE.search(window)
            if m:
                year = int(m.group(1))

        if year is None:
            # fallback: primer año que aparezca en el sample
            m = _YEAR_RE.search(text_sample)
            if m:
                year = int(m.group(1))

        return DocumentInfo(
            is_pdf=True,
            is_digital_pdf=is_digital,
            pages=pages,
            statement_year=year,
        )

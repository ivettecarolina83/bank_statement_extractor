from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import pdfplumber


BEGIN_RE = re.compile(r"Beginning balance on\s+(\d{1,2}/\d{1,2})\s+\$?([0-9,]+\.\d{2})", re.IGNORECASE)
END_RE   = re.compile(r"Ending balance on\s+(\d{1,2}/\d{1,2})\s+\$?([0-9,]+\.\d{2})", re.IGNORECASE)

# Muy simple: si en el texto aparece "Savings" cerca, lo atribuimos a Savings; si no, Checking.
def _guess_account(text: str) -> str:
    t = text.lower()
    if "savings" in t:
        return "Savings"
    return "Checking"

def _to_float(s: str) -> float:
    return float(s.replace(",", ""))

def extract_begin_end(pdf_path: str) -> Dict[str, Tuple[Optional[Tuple[str, float]], Optional[Tuple[str, float]]]]:
    """
    Devuelve:
      {
        "Checking": (("3/12", 0.00), ("4/5", 312.54)),
        "Savings":  ((...), (...))
      }
    Si no encuentra alguno, lo deja en None.
    """
    out: Dict[str, Tuple[Optional[Tuple[str, float]], Optional[Tuple[str, float]]]] = {
        "Checking": (None, None),
        "Savings": (None, None),
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if not txt.strip():
                continue

            acct = _guess_account(txt)

            b = BEGIN_RE.search(txt)
            e = END_RE.search(txt)

            cur_b, cur_e = out.get(acct, (None, None))

            if b and cur_b is None:
                out[acct] = ((b.group(1), _to_float(b.group(2))), cur_e)

            cur_b, cur_e = out.get(acct, (None, None))
            if e and cur_e is None:
                out[acct] = (cur_b, (e.group(1), _to_float(e.group(2))))

    return out

def main() -> int:
    pdf_path = "samples/wells_fargo_sample.pdf"
    json_path = "out.json"

    # 1) Lee out.json
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    accounts = data.get("accounts", [])

    # 2) Extrae beginning/ending del PDF
    be = extract_begin_end(pdf_path)

    print("=== VALIDACIÓN BEGIN/END vs SUM ===")
    for a in accounts:
        name = a["name"]
        tx = a.get("transactions", [])
        s = round(sum(t["amount"] for t in tx), 2)
        last_bal = tx[-1]["balance"] if tx else None

        begin, end = be.get(name, (None, None))

        print(f"\nACCOUNT: {name}")
        print(f"  tx_count      = {len(tx)}")
        print(f"  sum(amounts)  = {s}")
        print(f"  last_balance  = {last_bal}")

        if begin:
            print(f"  begin_balance = {begin[1]} (on {begin[0]})")
        else:
            print("  begin_balance = NOT FOUND")

        if end:
            print(f"  end_balance   = {end[1]} (on {end[0]})")
        else:
            print("  end_balance   = NOT FOUND")

        # Chequeo contable si tenemos begin y end
        if begin and end:
            expected_end = round(begin[1] + s, 2)
            ok = (expected_end == round(end[1], 2))
            print(f"  expected_end  = {expected_end}  ->  {'OK' if ok else 'MISMATCH'}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

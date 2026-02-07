from __future__ import annotations

import argparse
import pdfplumber


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="PDF path")
    ap.add_argument("--page", type=int, default=0, help="0-index page")
    ap.add_argument("--ymin", type=float, default=0.0, help="top boundary (smaller = higher)")
    ap.add_argument("--ymax", type=float, default=99999.0, help="bottom boundary")
    args = ap.parse_args()

    with pdfplumber.open(args.pdf) as pdf:
        page = pdf.pages[args.page]
        print(f"PAGE {args.page+1}/{len(pdf.pages)} size={page.width}x{page.height}")

        text = page.extract_text() or ""
        print("\n--- TEXT (first 120 lines) ---")
        for i, line in enumerate(text.splitlines()[:120], start=1):
            print(f"{i:03d}: {line}")

        print("\n--- TABLES (extract_tables) ---")
        tables = page.extract_tables()
        print(f"tables found: {len(tables)}")

        print("\n--- WORDS (with coords) ---")
        words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
        print(f"words found: {len(words)}")
        shown = 0

        for w in words:
            top = w["top"]
            if top < args.ymin or top > args.ymax:
                continue

            # imprimir palabras clave + montos + columnas típicas
            txt = w["text"]
            is_moneyish = any(ch.isdigit() for ch in txt) and ("." in txt or "," in txt)
            is_interesting = (
                txt in ("Transaction", "history", "Transaction history", "Date", "Description", "Deposits", "Withdrawals", "Ending", "balance")
                or is_moneyish
                or txt.count("/") == 1  # fechas M/D
            )

            if is_interesting:
                print(f'{txt:30} x0={w["x0"]:7.2f} x1={w["x1"]:7.2f} top={w["top"]:7.2f} bottom={w["bottom"]:7.2f}')
                shown += 1
                if shown >= 250:
                    break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

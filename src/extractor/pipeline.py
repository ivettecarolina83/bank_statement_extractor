from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

from .banks.wells_fargo import extract as extract_wells


def main() -> int:
    parser = argparse.ArgumentParser(description="Bank Statement Extractor (MVP)")
    parser.add_argument("file", help="Ruta al PDF")
    parser.add_argument("--out", default="", help="Ruta de salida JSON (opcional)")
    args = parser.parse_args()

    pdf_path = Path(args.file)
    if not pdf_path.exists():
        raise SystemExit(f"No existe el archivo: {pdf_path}")

    console = Console()
    console.print(f"Procesando: {pdf_path}", style="bold")

    result = extract_wells(str(pdf_path))
    payload = result.model_dump()

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"OK -> {out_path}", style="bold green")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    total = sum(len(a["transactions"]) for a in payload["accounts"])
    console.print(f"Transacciones detectadas: {total}", style="bold cyan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

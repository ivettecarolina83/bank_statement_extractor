import pdfplumber

PDF_PATH = "samples/wells_fargo_sample.pdf"

hits = []

with pdfplumber.open(PDF_PATH) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Transaction history" in text:
            hits.append(i)

print("pages_with_transaction_history =", hits)

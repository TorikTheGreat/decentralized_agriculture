#!/usr/bin/env python3
"""
Extract machine-readable text from all PDFs in sources/.

For each PDF:
  1. Try to extract the embedded text layer with PyMuPDF (fast, exact).
  2. For any page with little/no embedded text, fall back to Tesseract OCR.

Output: sources/ocr/<filename>.txt

Usage:
    .venv/bin/python utils/extract_text.py                      # process all PDFs
    .venv/bin/python utils/extract_text.py --file sources/x.pdf # process a single PDF
    .venv/bin/python utils/extract_text.py --force               # re-extract even if .txt exists and is newer

Requirements (in .venv):
    pip install PyMuPDF pytesseract Pillow
System:
    sudo apt install tesseract-ocr
"""

import argparse
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Minimum characters on a page before we consider the text layer usable.
# Pages with fewer chars than this get OCR'd instead.
MIN_CHARS_PER_PAGE = 100

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"
OCR_DIR = SOURCES_DIR / "ocr"


def extract_page_text(page: fitz.Page) -> tuple[str, str]:
    """Extract text from a single page. Returns (text, method)."""
    text = page.get_text()
    if len(text.strip()) >= MIN_CHARS_PER_PAGE:
        return text, "embedded"

    # Fall back to OCR: render page to image at 300 DPI
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    ocr_text = pytesseract.image_to_string(img)
    return ocr_text, "ocr"


def extract_pdf(pdf_path: Path, out_path: Path) -> dict:
    """Extract text from a PDF. Returns stats about the extraction."""
    doc = fitz.open(pdf_path)
    stats = {"pages": len(doc), "embedded": 0, "ocr": 0}
    all_text = []

    for i, page in enumerate(doc):
        text, method = extract_page_text(page)
        stats[method] += 1
        all_text.append(f"--- Page {i + 1} ---\n{text}")

    doc.close()

    out_path.write_text("\n".join(all_text), encoding="utf-8")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Extract text from source PDFs")
    parser.add_argument("--force", action="store_true", help="Re-extract all, ignoring timestamps")
    parser.add_argument("--file", type=Path, help="Process a single PDF instead of all")
    args = parser.parse_args()

    OCR_DIR.mkdir(exist_ok=True)

    if args.file:
        pdf_path = args.file.resolve()
        if not pdf_path.exists():
            print(f"File not found: {pdf_path}")
            sys.exit(1)
        pdfs = [pdf_path]
    else:
        pdfs = sorted(SOURCES_DIR.glob("*.pdf"))
        if not pdfs:
            print("No PDFs found in", SOURCES_DIR)
            sys.exit(1)

    extracted = 0
    skipped = 0
    ocr_needed = []

    for pdf_path in pdfs:
        out_path = OCR_DIR / (pdf_path.stem + ".txt")

        # Skip if output exists and is newer than the PDF
        if not args.force and out_path.exists() and out_path.stat().st_mtime > pdf_path.stat().st_mtime:
            skipped += 1
            continue

        print(f"  {pdf_path.name} ... ", end="", flush=True)
        try:
            stats = extract_pdf(pdf_path, out_path)
            extracted += 1
            if stats["ocr"] > 0:
                ocr_needed.append((pdf_path.name, stats))
                print(f"{stats['pages']} pages ({stats['embedded']} embedded, {stats['ocr']} OCR)")
            else:
                print(f"{stats['pages']} pages (all embedded text)")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\nDone: {extracted} extracted, {skipped} skipped (up to date)")
    if ocr_needed:
        print(f"\n{len(ocr_needed)} PDFs required OCR on some pages (quality may vary):")
        for name, stats in ocr_needed:
            print(f"  - {name}: {stats['ocr']}/{stats['pages']} pages OCR'd")


if __name__ == "__main__":
    main()

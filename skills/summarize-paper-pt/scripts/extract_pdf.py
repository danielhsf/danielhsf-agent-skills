#!/usr/bin/env python3
"""Extract raw text from a paper PDF.

Handles the annoying cases common in academic papers:
  - Two-column layout: detected per page; columns are read in order
    (left column top-to-bottom, then right), and full-width blocks like
    title/abstract on the first page are kept in their natural position.
  - Scanned PDFs (no embedded text): falls back to OCR via pytesseract
    when available, otherwise reports which pages need OCR and how to
    enable it.
  - Long PDFs (>20 pages): output is split into numbered part files so
    each chunk stays comfortably readable.

Usage:
    python scripts/extract_pdf.py paper.pdf
    python scripts/extract_pdf.py paper.pdf -o /tmp/out.txt --pages 1-10
    python scripts/extract_pdf.py scanned.pdf --ocr-lang eng+por

Dependencies:
    pip install pdfplumber            # required (pypdf works as a degraded fallback)
    pip install pytesseract           # only for scanned PDFs...
    sudo apt install tesseract-ocr    # ...plus the tesseract binary
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Fraction of the page width used as the gutter half-width when deciding
# whether a line crosses the center of the page.
GUTTER_TOLERANCE = 0.04
# Minimum empty gap (fraction of page width) around the center for a line
# that spans it to count as two column lines at the same height instead of
# a genuine full-width line — real column gutters are much wider than the
# space between two words in a centered title.
COLUMN_GAP_MIN = 0.02
# Pages with fewer extracted characters than this are treated as scanned.
MIN_CHARS_PER_PAGE = 40
# Pages need at least this many words before two-column detection is trusted.
MIN_WORDS_FOR_LAYOUT = 30
# Vertical tolerance (points) when grouping words into lines.
LINE_Y_TOLERANCE = 3.0

PAGE_MARKER = "\n\n--- Página {n} ---\n\n"


def parse_page_ranges(spec: str, page_count: int) -> list[int]:
    """Parse '1-10', '5', '1-3,7' into 0-based page indexes."""
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start) - 1, int(end)))
        else:
            pages.add(int(part) - 1)
    valid = sorted(p for p in pages if 0 <= p < page_count)
    if not valid:
        raise ValueError(f"page range '{spec}' selects no pages (PDF has {page_count})")
    return valid


def group_into_lines(words: list[dict]) -> list[list[dict]]:
    """Group pdfplumber words into visual lines by vertical position."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(word["top"] - lines[-1][0]["top"]) <= LINE_Y_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return lines


def classify_line(
    line: list[dict], mid: float, page_width: float
) -> tuple[str, list[dict], list[dict]]:
    """Classify a visual line relative to the page center.

    Returns (kind, left_words, right_words) where kind is one of:
      'left'/'right' — the line sits entirely on one side;
      'pair' — words on both sides separated by a wide empty gutter
               (two column lines at the same height);
      'full' — the line genuinely spans the center (title, abstract,
               single-column body text).
    """
    x0 = min(w["x0"] for w in line)
    x1 = max(w["x1"] for w in line)
    gutter = page_width * GUTTER_TOLERANCE
    if x1 <= mid + gutter:
        return "left", line, []
    if x0 >= mid - gutter:
        return "right", [], line
    left_words = [w for w in line if (w["x0"] + w["x1"]) / 2 < mid]
    right_words = [w for w in line if (w["x0"] + w["x1"]) / 2 >= mid]
    if left_words and right_words:
        gap_start = max(w["x1"] for w in left_words)
        gap_end = min(w["x0"] for w in right_words)
        if gap_end - gap_start >= page_width * COLUMN_GAP_MIN and gap_start <= mid <= gap_end:
            return "pair", left_words, right_words
    return "full", left_words, right_words


def looks_two_column(words: list[dict], page_width: float) -> bool:
    """Heuristic: almost no line runs continuously across the page center,
    yet there is substantial text on both sides. Single-column text fails
    this because most of its lines cross the center without a gap."""
    if len(words) < MIN_WORDS_FOR_LAYOUT:
        return False
    mid = page_width / 2
    lines = group_into_lines(words)
    counts = {"left": 0, "right": 0, "pair": 0, "full": 0}
    for line in lines:
        kind, _, _ = classify_line(line, mid, page_width)
        counts[kind] += 1
    left = counts["left"] + counts["pair"]
    right = counts["right"] + counts["pair"]
    return counts["full"] / len(lines) < 0.2 and left >= 3 and right >= 3


def line_text(line: list[dict]) -> str:
    return " ".join(w["text"] for w in sorted(line, key=lambda w: w["x0"]))


def extract_two_column(words: list[dict], page_width: float) -> str:
    """Rebuild reading order for a two-column page.

    Lines that span the page center (title, abstract, wide figures'
    captions) are emitted in place; runs of column lines are emitted as
    left column first, then right column.
    """
    mid = page_width / 2
    blocks: list[str] = []
    left_run: list[str] = []
    right_run: list[str] = []

    def flush_columns() -> None:
        if left_run or right_run:
            blocks.append("\n".join(left_run + right_run))
            left_run.clear()
            right_run.clear()

    for line in group_into_lines(words):
        kind, left_words, right_words = classify_line(line, mid, page_width)
        if kind == "full":
            flush_columns()
            blocks.append(line_text(line))
        else:
            if left_words:
                left_run.append(line_text(left_words))
            if right_words:
                right_run.append(line_text(right_words))
    flush_columns()
    return "\n".join(blocks)


def ocr_page(page, lang: str) -> str:
    """Rasterize a pdfplumber page and run tesseract on it."""
    import pytesseract  # noqa: PLC0415 — optional dependency

    image = page.to_image(resolution=300).original
    return pytesseract.image_to_string(image, lang=lang)


def ocr_available() -> tuple[bool, str]:
    try:
        import pytesseract
    except ImportError:
        return False, "pip install pytesseract"
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False, "sudo apt install tesseract-ocr"
    return True, ""


def extract_with_pdfplumber(
    pdf_path: Path, page_indexes: list[int] | None, ocr_lang: str
) -> tuple[list[tuple[int, str]], dict]:
    import pdfplumber  # noqa: PLC0415 — checked by caller

    stats = {"two_column": [], "ocr": [], "needs_ocr": [], "page_count": 0}
    results: list[tuple[int, str]] = []
    can_ocr, ocr_hint = ocr_available()

    with pdfplumber.open(pdf_path) as pdf:
        stats["page_count"] = len(pdf.pages)
        indexes = page_indexes if page_indexes is not None else range(len(pdf.pages))
        for i in indexes:
            page = pdf.pages[i]
            # Drop rotated text (e.g. the vertical arXiv watermark on the
            # left margin), which would otherwise interleave with the body.
            words = [w for w in page.extract_words(use_text_flow=False) if w.get("upright", True)]
            if looks_two_column(words, page.width):
                text = extract_two_column(words, page.width)
                stats["two_column"].append(i + 1)
            else:
                text = page.extract_text() or ""

            if len(text.strip()) < MIN_CHARS_PER_PAGE:
                if can_ocr:
                    text = ocr_page(page, ocr_lang)
                    stats["ocr"].append(i + 1)
                else:
                    stats["needs_ocr"].append(i + 1)
                    stats["ocr_hint"] = ocr_hint
                    text = text.strip() or "[página sem texto extraível — provavelmente escaneada]"
            results.append((i + 1, text))
    return results, stats


def extract_with_pypdf(pdf_path: Path, page_indexes: list[int] | None) -> tuple[list[tuple[int, str]], dict]:
    import pypdf  # noqa: PLC0415 — checked by caller

    reader = pypdf.PdfReader(pdf_path)
    stats = {"two_column": [], "ocr": [], "needs_ocr": [], "page_count": len(reader.pages)}
    results = []
    indexes = page_indexes if page_indexes is not None else range(len(reader.pages))
    for i in indexes:
        text = reader.pages[i].extract_text() or ""
        if len(text.strip()) < MIN_CHARS_PER_PAGE:
            stats["needs_ocr"].append(i + 1)
            text = text.strip() or "[página sem texto extraível — provavelmente escaneada]"
        results.append((i + 1, text))
    return results, stats


def write_output(
    pages: list[tuple[int, str]], output: Path, split_every: int
) -> list[Path]:
    """Write one file, or numbered part files when the PDF is long."""
    if split_every <= 0 or len(pages) <= split_every:
        chunks = [pages]
    else:
        chunks = [pages[i : i + split_every] for i in range(0, len(pages), split_every)]

    written: list[Path] = []
    for n, chunk in enumerate(chunks, start=1):
        if len(chunks) == 1:
            path = output
        else:
            first, last = chunk[0][0], chunk[-1][0]
            path = output.with_name(f"{output.stem}-part{n:02d}-p{first}-{last}{output.suffix}")
        body = "".join(PAGE_MARKER.format(n=num) + text for num, text in chunk)
        path.write_text(body.lstrip("\n"), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", type=Path, help="caminho do PDF")
    parser.add_argument("-o", "--output", type=Path, help="arquivo de saída (padrão: <pdf>-text.txt ao lado do PDF)")
    parser.add_argument("--pages", help="páginas a extrair, ex.: '1-10' ou '1-3,7'")
    parser.add_argument(
        "--split-every",
        type=int,
        default=20,
        metavar="N",
        help="divide a saída em partes de N páginas quando o PDF é longo (0 desativa; padrão: 20)",
    )
    parser.add_argument("--ocr-lang", default="eng+por", help="idiomas do tesseract para OCR (padrão: eng+por)")
    args = parser.parse_args()

    if not args.pdf.is_file():
        parser.error(f"arquivo não encontrado: {args.pdf}")
    output = args.output or args.pdf.with_name(args.pdf.stem + "-text.txt")

    try:
        import pdfplumber  # noqa: F401
        engine = "pdfplumber"
    except ImportError:
        try:
            import pypdf  # noqa: F401
            engine = "pypdf"
            print(
                "AVISO: pdfplumber não instalado; usando pypdf. Layout de duas colunas "
                "pode sair fora de ordem. Instale com: pip install pdfplumber",
                file=sys.stderr,
            )
        except ImportError:
            print(
                "ERRO: nenhuma biblioteca de PDF disponível.\n"
                "Instale com: pip install pdfplumber",
                file=sys.stderr,
            )
            return 1

    if engine == "pdfplumber":
        import pdfplumber
        with pdfplumber.open(args.pdf) as pdf:
            page_count = len(pdf.pages)
    else:
        import pypdf
        page_count = len(pypdf.PdfReader(args.pdf).pages)

    page_indexes = parse_page_ranges(args.pages, page_count) if args.pages else None

    if engine == "pdfplumber":
        pages, stats = extract_with_pdfplumber(args.pdf, page_indexes, args.ocr_lang)
    else:
        pages, stats = extract_with_pypdf(args.pdf, page_indexes)

    written = write_output(pages, output, args.split_every)

    print(f"PDF: {args.pdf.name} ({stats['page_count']} páginas, {len(pages)} extraídas via {engine})")
    if stats["two_column"]:
        print(f"Layout de duas colunas detectado em {len(stats['two_column'])} página(s).")
    if stats["ocr"]:
        print(f"OCR aplicado nas páginas: {', '.join(map(str, stats['ocr']))}")
    if stats["needs_ocr"]:
        hint = stats.get("ocr_hint", "pip install pytesseract && sudo apt install tesseract-ocr")
        print(
            f"ATENÇÃO: {len(stats['needs_ocr'])} página(s) sem texto extraível "
            f"(provavelmente escaneadas): {', '.join(map(str, stats['needs_ocr']))}\n"
            f"Para habilitar OCR: {hint}",
            file=sys.stderr,
        )
    for path in written:
        print(f"Saída: {path}")
    if len(written) > 1:
        print(f"(PDF longo: saída dividida em {len(written)} partes de até {args.split_every} páginas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

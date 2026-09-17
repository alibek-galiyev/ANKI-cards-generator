"""Multi-format book text extractors supporting .epub, .fb2, .txt, .pdf, .mobi, and .csv."""

import csv
import logging
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

logger = logging.getLogger(__name__)


def extract_epub(file_path: str) -> list[str]:
    """Extract text sections from an EPUB eBook."""
    book = epub.read_epub(file_path)
    sections = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator=" ").strip()
        if len(text) > 200:
            sections.append(text)
    return sections


def extract_fb2(file_path: str) -> list[str]:
    """Extract paragraphs from FictionBook 2.0 (XML) eBook."""
    with open(file_path, "rb") as f:
        content = f.read()

    paragraphs = []
    try:
        root = ET.fromstring(content)
        for elem in root.iter():
            if elem.tag.endswith("p") and elem.text:
                txt = elem.text.strip()
                if txt:
                    paragraphs.append(txt)
    except ET.ParseError:
        soup = BeautifulSoup(content, "html.parser")
        paragraphs = [
            p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()
        ]

    sections = []
    current_chunk, current_len = [], 0
    for p in paragraphs:
        current_chunk.append(p)
        current_len += len(p)
        if current_len >= 10000:
            sections.append(" ".join(current_chunk))
            current_chunk, current_len = [], 0
    if current_chunk:
        sections.append(" ".join(current_chunk))
    return sections


def extract_txt(file_path: str) -> list[str]:
    """Extract text from plain text (.txt) file with automatic encoding fallback."""
    text = ""
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    sections = []
    current_chunk, current_len = [], 0
    for p in paragraphs:
        current_chunk.append(p)
        current_len += len(p)
        if current_len >= 10000:
            sections.append(" ".join(current_chunk))
            current_chunk, current_len = [], 0
    if current_chunk:
        sections.append(" ".join(current_chunk))
    return sections


def extract_pdf(file_path: str) -> list[str]:
    """Extract text page-by-page from digital PDF using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    sections = []
    current_chunk, current_len = [], 0
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            page_text = page_text.strip()
            current_chunk.append(page_text)
            current_len += len(page_text)
            if current_len >= 10000:
                sections.append(" ".join(current_chunk))
                current_chunk, current_len = [], 0
    if current_chunk:
        sections.append(" ".join(current_chunk))
    return sections


def extract_mobi(file_path: str) -> list[str]:
    """Extract text from Amazon MOBI / AZW eBook."""
    import mobi

    tempdir, extracted_path = mobi.extract(file_path)
    sections = []
    try:
        extracted_file = Path(extracted_path)
        if extracted_file.is_dir():
            html_files = list(extracted_file.glob("**/*.html")) + list(
                extracted_file.glob("**/*.xhtml")
            )
            for hf in html_files:
                content = hf.read_text(encoding="utf-8", errors="ignore")
                soup = BeautifulSoup(content, "html.parser")
                txt = soup.get_text(separator=" ").strip()
                if len(txt) > 200:
                    sections.append(txt)
        elif extracted_file.is_file():
            ext = extracted_file.suffix.lower()
            if ext in (".html", ".xhtml", ".htm"):
                content = extracted_file.read_text(encoding="utf-8", errors="ignore")
                soup = BeautifulSoup(content, "html.parser")
                txt = soup.get_text(separator=" ").strip()
                if len(txt) > 200:
                    sections.append(txt)
            elif ext == ".epub":
                sections = extract_epub(str(extracted_file))
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
    return sections


def extract_csv(file_path: str) -> list[str]:
    """Extract text content from CSV rows."""
    sections = []
    current_chunk, current_len = [], 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for row in reader:
            row_text = " ".join(cell.strip() for cell in row if cell.strip())
            if row_text:
                current_chunk.append(row_text)
                current_len += len(row_text)
                if current_len >= 10000:
                    sections.append(" ".join(current_chunk))
                    current_chunk, current_len = [], 0
    if current_chunk:
        sections.append(" ".join(current_chunk))
    return sections


def extract_text_sections(file_path: str) -> list[str]:
    """Inspect file extension and extract text sections cleanly."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Book file not found: '{file_path}'")

    ext = path.suffix.lower()
    logger.info("Extracting text from '%s' (format: %s)", file_path, ext)

    if ext == ".epub":
        return extract_epub(file_path)
    elif ext == ".fb2":
        return extract_fb2(file_path)
    elif ext == ".txt":
        return extract_txt(file_path)
    elif ext == ".pdf":
        return extract_pdf(file_path)
    elif ext in (".mobi", ".azw", ".azw3"):
        return extract_mobi(file_path)
    elif ext == ".csv":
        return extract_csv(file_path)
    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: .epub, .fb2, .txt, .pdf, .mobi, .csv"
        )

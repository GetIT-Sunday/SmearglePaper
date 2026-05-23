from __future__ import annotations

import urllib.request
from pathlib import Path

from .config import DATA_DIR
from .models import PaperMeta
from .storage import ensure_parent, write_json


class PaperReader:
    def read(self, paper: PaperMeta) -> dict[str, object]:
        pdf_path = DATA_DIR / "pdfs" / f"{paper.paper_id.replace('/', '_')}.pdf"
        text = ""
        figures: list[str] = []
        if paper.pdf_url:
            ensure_parent(pdf_path)
            try:
                download_file(paper.pdf_url, pdf_path, timeout=45)
                text = extract_pdf_text(pdf_path)
                figures = extract_pdf_figures(pdf_path, paper.paper_id)
            except Exception as exc:  # noqa: BLE001 - reported in output for local diagnosis
                text = f"PDF download/parse failed: {exc}"
        payload = {"paper": paper.to_dict(), "pdf_path": str(pdf_path) if pdf_path.exists() else None, "text": text[:30000], "figures": figures}
        out = DATA_DIR / "parsed" / f"{paper.paper_id.replace('/', '_')}.json"
        write_json(out, payload)
        return {"paper_id": paper.paper_id, "parsed": str(out), "text_chars": len(text), "figures": figures}


def download_file(url: str, path: Path, timeout: int = 45) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "SmearglePaper/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        path.write_bytes(response.read())


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages[:12]:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip()


def extract_pdf_figures(path: Path, paper_id: str, max_figures: int = 3) -> list[str]:
    try:
        import fitz
    except ImportError:
        return []

    out_dir = DATA_DIR / "figures" / paper_id.replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(path)
    candidates: list[tuple[int, int, bytes, str]] = []
    for page_index in range(min(len(doc), 8)):
        for image_index, image in enumerate(doc[page_index].get_images(full=True)):
            xref = image[0]
            extracted = doc.extract_image(xref)
            width = int(extracted.get("width", 0))
            height = int(extracted.get("height", 0))
            payload = extracted.get("image", b"")
            ext = str(extracted.get("ext", "png"))
            area = width * height
            if area >= 30_000 and payload:
                candidates.append((area, image_index, payload, ext))

    candidates.sort(key=lambda item: item[0], reverse=True)
    paths: list[str] = []
    for idx, (_, _, payload, ext) in enumerate(candidates[:max_figures], start=1):
        fig_path = out_dir / f"figure_{idx}.{ext}"
        fig_path.write_bytes(payload)
        paths.append(str(fig_path))

    if not paths and len(doc):
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
        fig_path = out_dir / "page_1_preview.png"
        pix.save(fig_path)
        paths.append(str(fig_path))
    doc.close()
    return paths

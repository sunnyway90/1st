from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PdfConversionError(RuntimeError):
    pass


def html_to_pdf(
    html_path: Path,
    pdf_path: Path,
    *,
    asset_source_dir: Path | None = None,
) -> Path:
    html_path = html_path.resolve()
    if not html_path.exists():
        raise PdfConversionError(f"HTML file not found: {html_path}")

    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    base_dir = (asset_source_dir or html_path.parent).resolve()

    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise PdfConversionError(
            "WeasyPrint is required for html-to-pdf. Install project dependencies with "
            "`python3 -m pip install -e .`."
        ) from exc

    try:
        HTML(filename=str(html_path), base_url=base_dir.as_uri() + "/").write_pdf(str(pdf_path))
    except Exception as exc:  # noqa: BLE001 - surface renderer failure
        raise PdfConversionError(f"Failed to render PDF for {html_path.name}: {exc}") from exc

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise PdfConversionError(f"Failed to render PDF for {html_path.name}: empty output")
    return pdf_path


def find_chrome_binary() -> str | None:
    for candidate in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
    ):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> Path:
    if not pdf_paths:
        raise PdfConversionError("No PDF files to merge.")

    writer = PdfWriter()
    for pdf_path in pdf_paths:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def combine_html_documents(html_paths: list[Path], output_path: Path) -> Path:
    sections: list[str] = []
    for html_path in html_paths:
        content = html_path.read_text(encoding="utf-8")
        extracted = _extract_renderable_html(content)
        sections.append(
            f'<section class="article-chunk" style="page-break-after: always;">{extracted}</section>'
        )

    combined = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Combined Articles</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.7; color: #222; }}
    img {{ max-width: 100%; height: auto; }}
    .article-chunk:last-child {{ page-break-after: auto; }}
  </style>
</head>
<body>
{"".join(sections)}
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined, encoding="utf-8")
    return output_path


def _extract_renderable_html(content: str) -> str:
    lower = content.lower()
    for tag in ("<article", "<body"):
        start = lower.find(tag)
        if start == -1:
            continue
        end = lower.find(f"</{tag[1:]}", start)
        if end != -1:
            fragment = content[start:end]
            open_end = fragment.find(">")
            if open_end != -1:
                return fragment[open_end + 1 :]
    return content


def batch_html_to_pdf(
    input_dir: Path,
    output_dir: Path,
    *,
    group_size: int = 1,
    merge_volumes: int | None = None,
) -> list[Path]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    html_files = sorted(input_dir.glob("*.html"))
    if not html_files:
        raise PdfConversionError(f"No HTML files found in {input_dir}")

    if group_size < 1:
        raise ValueError("group_size must be >= 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []

    if group_size == 1:
        for html_path in html_files:
            pdf_path = output_dir / f"{html_path.stem}.pdf"
            rendered.append(html_to_pdf(html_path, pdf_path, asset_source_dir=input_dir))
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for volume_index, start in enumerate(range(0, len(html_files), group_size), start=1):
                chunk = html_files[start : start + group_size]
                combined_html = temp_root / f"volume_{volume_index:03d}.html"
                combine_html_documents(chunk, combined_html)
                pdf_path = output_dir / f"volume_{volume_index:03d}.pdf"
                rendered.append(
                    html_to_pdf(combined_html, pdf_path, asset_source_dir=input_dir)
                )

    if merge_volumes and merge_volumes > 1:
        merged_paths: list[Path] = []
        for volume_index, start in enumerate(range(0, len(rendered), merge_volumes), start=1):
            chunk = rendered[start : start + merge_volumes]
            merged_path = output_dir / f"merged_{volume_index:03d}.pdf"
            merged_paths.append(merge_pdfs(chunk, merged_path))
        return merged_paths

    return rendered

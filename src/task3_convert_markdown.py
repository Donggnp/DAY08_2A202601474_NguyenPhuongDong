"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft:
    https://github.com/microsoft/markitdown

Cài đặt:
    pip install "markitdown[pdf]"
    # Lưu ý: cần extra [pdf] để convert được file PDF. Chỉ "pip install markitdown"
    # (không có extra) sẽ báo MissingDependencyException khi convert PDF, dù JSON/DOCX
    # vẫn convert bình thường.

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục
"""

import json
import sys
from pathlib import Path

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"



def convert_legal_docs():
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()

    for filepath in legal_dir.iterdir():
        if filepath.is_file() and filepath.suffix.lower() in (".pdf", ".docx", ".doc"):
            print(f"Converting: {filepath.name}")
            output_path = output_dir / f"{filepath.stem}.md"
            try:
                result = md.convert(str(filepath))
                content = result.text_content
                if not content or len(content.strip()) < 50:
                    print(f"  ⚠ PDF convert returned empty content for {filepath.name}")
                output_path.write_text(content, encoding="utf-8")
                print(f"  ✓ Saved: {output_path} ({len(content)} chars)")
            except Exception as e:
                print(f"  ❌ Convert lỗi đối với {filepath.name}: {e}")


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filepath in news_dir.iterdir():
        if filepath.is_file() and filepath.suffix.lower() == ".json":
            print(f"Converting: {filepath.name}")
            output_path = output_dir / f"{filepath.stem}.md"
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                title = data.get("title", "Unknown")
                url = data.get("url", "N/A")
                date_crawled = data.get("date_crawled", "N/A")
                body = data.get("content_markdown", "")

                header = f"# {title}\n\n"
                header += f"**Source:** {url}\n"
                header += f"**Crawled:** {date_crawled}\n\n---\n\n"

                # Nếu body đã chứa header tiêu đề trùng lặp ở đầu, xử lý để không bị lặp tiêu đề
                if body.strip().startswith(f"# {title}"):
                    body = body.strip()[len(f"# {title}"):].strip()

                content = header + body
                output_path.write_text(content, encoding="utf-8")
                print(f"  ✓ Saved: {output_path} ({len(content)} chars)")
            except Exception as e:
                print(f"  ❌ Convert lỗi đối với {filepath.name}: {e}")



def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("\n--- News Articles ---")
    convert_news_articles()

    print("\n✓ Done! Output tại:", OUTPUT_DIR)


if __name__ == "__main__":
    convert_all()

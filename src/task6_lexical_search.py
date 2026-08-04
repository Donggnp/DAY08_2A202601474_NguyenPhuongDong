import re
import sys
from pathlib import Path

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from .task4_chunking_indexing import CHROMA_DIR, COLLECTION_NAME
except ImportError:
    from src.task4_chunking_indexing import CHROMA_DIR, COLLECTION_NAME

CORPUS: list[dict] = []  # List of {'content': str, 'metadata': dict}
BM25_INDEX = None
_CORPUS_SIGNATURE = None
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _tokenize(text: str) -> list[str]:
    """Tokenize text using regex word extraction."""
    return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)


def _load_chroma_corpus() -> list[dict]:
    """Use Task 4's exact chunks when ChromaDB is available."""
    try:
        import chromadb
    except ImportError:
        return []

    if not CHROMA_DIR.exists():
        return []
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(COLLECTION_NAME)
        stored = collection.get(include=["documents", "metadatas"])
    except Exception:
        return []

    documents = stored.get("documents") or []
    metadatas = stored.get("metadatas") or []
    return [
        {"content": content, "metadata": dict(metadata or {})}
        for content, metadata in zip(documents, metadatas)
        if isinstance(content, str) and content.strip()
    ]


def _load_markdown_corpus() -> list[dict]:
    """Fallback corpus from standardized Markdown documents."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if content:
            for i, paragraph in enumerate(content.split("\n\n")):
                p_text = paragraph.strip()
                if len(p_text) > 30:
                    documents.append({
                        "content": p_text,
                        "metadata": {
                            "source": path.name,
                            "type": "legal" if "legal" in str(path) else "news",
                            "chunk_index": i
                        }
                    })
    return documents


def load_corpus() -> list[dict]:
    """Prefer Chroma chunks; fall back to standardized Markdown documents."""
    return _load_chroma_corpus() or _load_markdown_corpus()


def _source_signature():
    markdown_files = tuple(
        (str(path), path.stat().st_mtime_ns, path.stat().st_size)
        for path in sorted(STANDARDIZED_DIR.rglob("*.md"))
    )
    chroma_db = CHROMA_DIR / "chroma.sqlite3"
    chroma_signature = (
        (chroma_db.stat().st_mtime_ns, chroma_db.stat().st_size)
        if chroma_db.exists()
        else None
    )
    return markdown_files, chroma_signature


def build_bm25_index(corpus: list[dict]):
    """Xây dựng BM25 index từ corpus."""
    if not corpus:
        return None
    from rank_bm25 import BM25Okapi
    tokenized_corpus = [_tokenize(doc.get("content", "")) for doc in corpus]
    return BM25Okapi(tokenized_corpus, k1=1.5, b=0.75)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Tìm kiếm từ khóa sử dụng BM25."""
    global CORPUS, BM25_INDEX, _CORPUS_SIGNATURE
    if top_k <= 0 or not query or not query.strip():
        return []

    signature = _source_signature()
    if signature != _CORPUS_SIGNATURE or (CORPUS and BM25_INDEX is None):
        CORPUS = load_corpus()
        BM25_INDEX = build_bm25_index(CORPUS)
        _CORPUS_SIGNATURE = signature

    if not CORPUS or BM25_INDEX is None:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scores = BM25_INDEX.get_scores(query_tokens)
    ranked_indices = sorted(
        range(len(scores)), key=lambda index: (-float(scores[index]), index)
    )

    return [
        {
            "content": CORPUS[index]["content"],
            "score": float(round(scores[index], 4)),
            "metadata": dict(CORPUS[index].get("metadata", {})),
        }
        for index in ranked_indices[:top_k]
        if float(scores[index]) > 0
    ]


if __name__ == "__main__":
    results = lexical_search("phương thức thanh toán shopee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")

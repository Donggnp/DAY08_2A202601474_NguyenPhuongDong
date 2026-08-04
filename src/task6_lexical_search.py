"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25. Nếu dùng phương pháp khác (TF-IDF, Elasticsearch,
Weaviate BM25 built-in), hãy giải thích cơ chế trong buổi demo → +5 bonus.

Cài đặt:
    pip install rank-bm25

BM25 hoạt động thế nào:
    - Term Frequency (TF): từ xuất hiện nhiều trong document → điểm cao
    - Inverse Document Frequency (IDF): từ hiếm → quan trọng hơn
    - Document length normalization: document dài không bị ưu tiên quá mức
    - Formula: score(q,d) = Σ IDF(qi) * (tf(qi,d) * (k1+1)) / (tf(qi,d) + k1*(1-b+b*|d|/avgdl))
    - k1=1.5 (term saturation), b=0.75 (length normalization)
"""

import re
from pathlib import Path

try:
    from .task4_chunking_indexing import CHROMA_DIR, COLLECTION_NAME
except ImportError:
    from task4_chunking_indexing import CHROMA_DIR, COLLECTION_NAME

CORPUS: list[dict] = []  # List of {'content': str, 'metadata': dict}
BM25_INDEX = None
_CORPUS_SIGNATURE = None
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _tokenize(text: str) -> list[str]:
    """Tokenize Vietnamese/English text without requiring a language model."""
    return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)


def _load_chroma_corpus() -> list[dict]:
    """Use Task 4's exact chunks when ChromaDB is installed and available."""
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
        # Task 6 remains usable while Role 2 is rebuilding/migrating ChromaDB.
        return []

    documents = stored.get("documents") or []
    metadatas = stored.get("metadatas") or []
    return [
        {"content": content, "metadata": dict(metadata or {})}
        for content, metadata in zip(documents, metadatas)
        if isinstance(content, str) and content.strip()
    ]


def _load_markdown_corpus() -> list[dict]:
    """Fallback corpus so BM25 works before ChromaDB has been built."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if content:
            documents.append({
                "content": content,
                "metadata": {
                    "source": str(path.relative_to(STANDARDIZED_DIR)),
                    "type": "legal" if "legal" in path.parts else "news",
                    "path": str(path),
                },
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
    """
    Xây dựng BM25 index từ corpus.

    Args:
        corpus: List of {'content': str, 'metadata': dict}
    """
    if not corpus:
        return None
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise ImportError(
            "Task 6 requires rank-bm25. Install it with: pip install rank-bm25"
        ) from exc

    tokenized_corpus = [_tokenize(doc.get("content", "")) for doc in corpus]
    return BM25Okapi(tokenized_corpus, k1=1.5, b=0.75)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,      # BM25 score
            'metadata': dict
        }
        Sorted by score descending.
    """
    global CORPUS, BM25_INDEX, _CORPUS_SIGNATURE
    if top_k <= 0 or not query.strip():
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
            "score": float(scores[index]),
            "metadata": dict(CORPUS[index].get("metadata", {})),
        }
        for index in ranked_indices[:top_k]
        if float(scores[index]) > 0
    ]


if __name__ == "__main__":
    # Test
    results = lexical_search("phương thức thanh toán shopee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")

import sys
from pathlib import Path

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from rank_bm25 import BM25Okapi

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

_corpus_chunks = []
_bm25_instance = None


def _get_corpus():
    global _corpus_chunks, _bm25_instance
    if _corpus_chunks:
        return _corpus_chunks, _bm25_instance

    _corpus_chunks = []
    if STANDARDIZED_DIR.exists():
        for md_file in STANDARDIZED_DIR.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            doc_type = "legal" if "legal" in str(md_file) else "news"
            # Tách đoạn thành các chunks nhỏ
            for i, paragraph in enumerate(content.split("\n\n")):
                p_text = paragraph.strip()
                if len(p_text) > 30:
                    _corpus_chunks.append({
                        "content": p_text,
                        "metadata": {
                            "source": md_file.name,
                            "type": doc_type,
                            "chunk_index": i
                        }
                    })

    if _corpus_chunks:
        tokenized_corpus = [doc["content"].lower().split() for doc in _corpus_chunks]
        _bm25_instance = BM25Okapi(tokenized_corpus)

    return _corpus_chunks, _bm25_instance


def build_bm25_index(corpus: list[dict]):
    """
    Xây dựng BM25 index từ corpus.
    """
    tokenized_corpus = [doc["content"].lower().split() for doc in corpus]
    return BM25Okapi(tokenized_corpus)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.
    """
    if not query or not query.strip():
        return []

    corpus, bm25 = _get_corpus()
    if not corpus or not bm25:
        return []

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    import numpy as np
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "content": corpus[idx]["content"],
                "score": float(round(scores[idx], 4)),
                "metadata": corpus[idx]["metadata"]
            })
    return results


if __name__ == "__main__":
    results = lexical_search("phương thức thanh toán shopee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")


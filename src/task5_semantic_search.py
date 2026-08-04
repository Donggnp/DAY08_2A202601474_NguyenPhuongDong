import sys

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from src.task4_chunking_indexing import embed_texts, get_collection
except ImportError:
    from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10, metadata_filter: dict = None) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity với ChromaDB và OpenAI embeddings.

    Args:
        query: Câu truy vấn người dùng
        top_k: Số lượng kết quả tối đa
        metadata_filter: Bộ lọc metadata (vd: {'customer_role': 'buyer'})

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index, customer_role...
        }
        Sorted by score descending.
    """
    if not query or not query.strip():
        return []

    collection = get_collection()
    count = collection.count()
    if count == 0:
        print("⚠ Collection ChromaDB trống. Hãy chạy Task 4 trước khi tìm kiếm!")
        return []

    # Bước 1: Embed query bằng OpenAI text-embedding-3-small
    query_vector = embed_texts([query])[0]

    # Bước 2: Query ChromaDB
    n_results = min(top_k, count)
    query_kwargs = {
        "query_embeddings": [query_vector],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"]
    }
    if metadata_filter:
        query_kwargs["where"] = metadata_filter

    results = collection.query(**query_kwargs)

    if not results or not results.get("documents") or not results["documents"][0]:
        return []

    # Bước 3: Chuyển đổi distance thành Cosine Similarity score (1.0 - distance)
    output = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        # ChromaDB Cosine distance = 1 - Cosine Similarity
        similarity = max(0.0, 1.0 - float(dist))
        output.append({
            "content": doc,
            "score": round(similarity, 4),
            "metadata": meta
        })

    # Sắp xếp giảm dần theo score
    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    test_query = "quy định trả hàng hoàn tiền shopee"
    print(f"\n--- Testing Semantic Search: '{test_query}' ---")
    results = semantic_search(test_query, top_k=5)
    for r in results:
        print(f"[{r['score']:.4f}] {r['metadata'].get('source')} (Role: {r['metadata'].get('customer_role')})")
        print(f"  {r['content'][:120]}...\n")


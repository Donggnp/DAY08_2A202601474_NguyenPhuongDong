"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) hoặc Qwen3-Reranker
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement — khuyến nghị vì không cần API key

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.

Lưu ý quan trọng về RRF (sẽ dùng lại ở Task 9): điểm RRF fused CHỈ phụ thuộc thứ hạng,
không phải độ tương đồng thật. Top-1 sau khi fuse luôn xấp xỉ 1/(k+1) ≈ 0.0164 (k=60),
bất kể nội dung đó có thật sự liên quan đến câu hỏi hay không. Đừng dùng điểm RRF để
quyết định fallback ở Task 9 — xem ghi chú ở đó.
"""

import os
import math

import requests
from dotenv import load_dotenv

load_dotenv()

JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"
JINA_RERANK_MODEL = "jina-reranker-v2-base-multilingual"


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder model.

    Args:
        query: Câu truy vấn
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số lượng kết quả sau rerank

    Returns:
        List of top_k candidates, re-scored và sorted by rerank_score descending.
    """
    if top_k <= 0 or not candidates:
        return []
    if not query.strip():
        raise ValueError("query must not be empty")

    api_key = os.getenv("JINA_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing JINA_API_KEY. Add it to the local .env file.")

    documents = []
    candidate_indices = []
    for index, candidate in enumerate(candidates):
        content = str(candidate.get("content", "")).strip()
        if content:
            documents.append(content)
            candidate_indices.append(index)
    if not documents:
        return []

    try:
        response = requests.post(
            JINA_RERANK_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "model": JINA_RERANK_MODEL,
                "query": query,
                "documents": documents,
                "top_n": min(top_k, len(documents)),
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Jina reranker request failed: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Jina reranker returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Jina reranker response must be a JSON object")

    api_results = payload.get("results")
    if not isinstance(api_results, list):
        raise RuntimeError("Jina reranker response does not contain a results list")

    reranked = []
    seen_result_indices: set[int] = set()
    for result in api_results:
        if not isinstance(result, dict):
            raise RuntimeError("Jina reranker returned an invalid result item")
        result_index = result.get("index")
        score = result.get("relevance_score")
        if (
            isinstance(result_index, bool)
            or not isinstance(result_index, int)
            or not 0 <= result_index < len(documents)
        ):
            raise RuntimeError("Jina reranker returned an invalid document index")
        if result_index in seen_result_indices:
            raise RuntimeError("Jina reranker returned a duplicate document index")
        seen_result_indices.add(result_index)

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
        ):
            raise RuntimeError("Jina reranker returned an invalid relevance score")

        candidate = dict(candidates[candidate_indices[result_index]])
        candidate["score"] = float(score)
        candidate["rerank_model"] = JINA_RERANK_MODEL
        reranked.append(candidate)

    reranked.sort(key=lambda item: item["score"], reverse=True)
    return reranked[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.

    MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))

    Args:
        query_embedding: Vector embedding của query
        candidates: List of {'content': str, 'score': float, 'embedding': list, 'metadata': dict}
        top_k: Số lượng kết quả
        lambda_param: Trade-off giữa relevance (1.0) và diversity (0.0)

    Returns:
        List of top_k candidates selected by MMR.
    """
    if top_k <= 0 or not candidates:
        return []
    if not 0.0 <= lambda_param <= 1.0:
        raise ValueError("lambda_param must be between 0 and 1")

    query_vector = _validate_embedding(query_embedding, "query_embedding")
    candidate_vectors = [
        _validate_embedding(candidate.get("embedding"), f"candidates[{index}].embedding")
        for index, candidate in enumerate(candidates)
    ]
    if any(len(vector) != len(query_vector) for vector in candidate_vectors):
        raise ValueError("all candidate embeddings must match query embedding dimension")

    selected: list[int] = []
    remaining = list(range(len(candidates)))
    selected_scores: dict[int, float] = {}

    for _ in range(min(top_k, len(candidates))):
        best_index = remaining[0]
        best_score = float("-inf")

        for index in remaining:
            relevance = _cosine_similarity(query_vector, candidate_vectors[index])
            redundancy = max(
                (
                    _cosine_similarity(candidate_vectors[index], candidate_vectors[chosen])
                    for chosen in selected
                ),
                default=0.0,
            )
            mmr_score = (
                lambda_param * relevance - (1.0 - lambda_param) * redundancy
            )
            if mmr_score > best_score:
                best_index = index
                best_score = mmr_score

        selected.append(best_index)
        selected_scores[best_index] = best_score
        remaining.remove(best_index)

    results = []
    for index in selected:
        result = dict(candidates[index])
        result["score"] = selected_scores[index]
        result["rerank_method"] = "mmr"
        results.append(result)
    return results


def _validate_embedding(embedding, name: str) -> list[float]:
    if not isinstance(embedding, (list, tuple)) or not embedding:
        raise ValueError(f"{name} must be a non-empty list of numbers")
    vector = []
    for value in embedding:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must contain only numbers")
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"{name} must contain only finite numbers")
        vector.append(numeric_value)
    if math.isclose(sum(value * value for value in vector), 0.0):
        raise ValueError(f"{name} must not be a zero vector")
    return vector


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot_product / (left_norm * right_norm)


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    RRF(d) = Σ 1 / (k + rank_r(d))

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số lượng kết quả cuối cùng
        k: Smoothing constant (default=60, từ paper Cormack et al. 2009)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    if top_k <= 0 or not ranked_lists:
        return []
    if k < 0:
        raise ValueError("k must be non-negative")

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    first_seen: dict[str, int] = {}
    for ranked_list in ranked_lists:
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ranked_list, start=1):
            content = item.get("content", "")
            if not content or content in seen_in_list:
                continue
            seen_in_list.add(content)
            scores[content] = scores.get(content, 0.0) + 1.0 / (k + rank)
            if content not in items:
                items[content] = dict(item)
                first_seen[content] = len(first_seen)

    ordered = sorted(scores, key=lambda text: (-scores[text], first_seen[text]))
    results = []
    for content in ordered[:top_k]:
        result = dict(items[content])
        result["score"] = scores[content]
        results.append(result)
    return results


# =============================================================================
# Main rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "rrf",  # "cross_encoder" | "mmr" | "rrf"
    query_embedding: list[float] | None = None,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        query: Câu truy vấn
        candidates: Danh sách candidates từ retrieval
        top_k: Số lượng kết quả sau rerank
        method: Phương pháp reranking
        query_embedding: Vector query do Task 5 cung cấp khi method="mmr"
        lambda_param: Mức cân bằng relevance/diversity cho MMR

    Returns:
        List of top_k reranked candidates.
    """
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        if query_embedding is None:
            raise ValueError("query_embedding is required when method='mmr'")
        return rerank_mmr(
            query_embedding,
            candidates,
            top_k=top_k,
            lambda_param=lambda_param,
        )
    elif method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    # Test with dummy data
    dummy_candidates = [
        {"content": "Chính sách trả hàng và hoàn tiền Shopee trong 15 ngày", "score": 0.8, "metadata": {}},
        {"content": "Các phương thức thanh toán hỗ trợ trên Shopee Vietnam", "score": 0.6, "metadata": {}},
        {"content": "Quy định đăng bán sản phẩm dành cho người bán", "score": 0.5, "metadata": {}},
    ]
    results = rerank("chính sách trả hàng shopee", dummy_candidates, top_k=2)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")

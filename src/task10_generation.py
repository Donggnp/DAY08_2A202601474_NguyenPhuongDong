import os
import sys
from dotenv import load_dotenv

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

try:
    from src.task9_retrieval_pipeline import retrieve
except ImportError:
    from .task9_retrieval_pipeline import retrieve


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn
# =============================================================================

# top_k: Số chunks đưa vào context
# Chọn 5 vì: đủ evidence mà không quá dài gây lost in the middle
TOP_K = 5

# top_p (nucleus sampling): Xác suất tích lũy cho token generation
# Chọn 0.9 vì: đủ đa dạng nhưng vẫn tập trung vào các câu trả lời chính xác
TOP_P = 0.9

# temperature: Độ ngẫu nhiên của output
# Chọn 0.3 vì: RAG cần tính chính xác factual cao, hạn chế LLM sáng tạo/bịa đặt
TEMPERATURE = 0.3

# LLM Model mặc định
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên nghiệp trả lời các câu hỏi về chính sách thương mại điện tử và hỗ trợ khách hàng (thanh toán, đổi trả, giao hàng, bảo mật, quy định người bán).

Quy tắc bắt buộc:
1. Chỉ sử dụng thông tin từ context được cung cấp — KHÔNG bịa đặt thông tin.
2. Mỗi khẳng định phải có trích dẫn nguồn ngay sau đó, ví dụ: [returns-refund-policy-shopee.pdf] hoặc [article_01.md].
3. Nếu context không đủ thông tin để trả lời câu hỏi → trả lời chính xác: "Tôi không thể xác minh thông tin này từ nguồn hiện có"
4. Trả lời bằng tiếng Việt, trình bày mạch lạc, rõ ràng theo cấu trúc đoạn văn.
5. Không tự suy luận hay mở rộng ngoài những gì được nêu trong context."""


# =============================================================================
# DOCUMENT REORDERING (tránh lost in the middle)
# =============================================================================

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh hiện tượng "lost in the middle".
    LLM ghi nhớ tốt thông tin ở ĐẦU và CUỐI prompt, hay bỏ sót thông tin ở GIỮA.
    Strategy: Đặt chunk tốt nhất ở đầu, tốt thứ hai ở cuối, kém nhất ở giữa.

    Input order (by score): [0, 1, 2, 3, 4]
    Output order:           [0, 2, 4, 3, 1]
    """
    if len(chunks) <= 2:
        return chunks

    front = chunks[::2]   # index 0, 2, 4
    back = chunks[1::2]   # index 1, 3 (đảo ngược lại thành 3, 1)
    return front + back[::-1]


# =============================================================================
# CONTEXT FORMATTING
# =============================================================================

def format_context(chunks: list[dict]) -> str:
    """
    Format chunks thành chuỗi context cho prompt kèm theo nhãn nguồn (source) để LLM cite.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source") or chunk.get("source") or f"Source {i}"
        doc_type = metadata.get("type", "unknown")
        context_parts.append(
            f"[Document {i} | Source: {source} | Type: {doc_type}]\n"
            f"{chunk['content']}\n"
        )
    return "\n---\n".join(context_parts)


# =============================================================================
# GENERATION
# =============================================================================

def generate_with_citation(query: str, top_k: int = TOP_K, reranking_method: str = "rrf") -> dict:
    """
    End-to-end RAG generation có trích dẫn nguồn (citation).
    """
    if not query or not query.strip():
        return {
            "answer": "Vui lòng nhập câu hỏi hợp lệ.",
            "sources": [],
            "retrieval_source": "none"
        }

    # Step 1: Retrieve chunks qua pipeline với phương pháp reranking đã chọn
    chunks = retrieve(query, top_k=top_k, reranking_method=reranking_method)


    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có",
            "sources": [],
            "retrieval_source": "none"
        }

    # Step 2: Reorder chunks để chống "lost in the middle"
    reordered = reorder_for_llm(chunks)

    # Step 3: Format context
    context = format_context(reordered)

    # Step 4: Build prompt
    user_message = f"Context:\n{context}\n\n---\n\nQuestion: {query}"

    # Step 5: Call LLM
    from openai import OpenAI

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if openrouter_key:
        client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
        model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
    elif openai_key:
        client = OpenAI(api_key=openai_key)
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    else:
        raise ValueError("Cần OPENROUTER_API_KEY hoặc OPENAI_API_KEY trong file .env!")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )

    answer = response.choices[0].message.content

    retrieval_src = "hybrid"
    if chunks and isinstance(chunks[0], dict) and "source" in chunks[0]:
        retrieval_src = chunks[0]["source"]

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_src
    }


if __name__ == "__main__":
    test_queries = [
        "Shopee hỗ trợ những phương thức thanh toán nào?",
        "Làm sao để yêu cầu đổi trả hay hoàn tiền?",
        "Cần chuẩn bị bằng chứng gì khi yêu cầu hoàn tiền?",
    ]

    for q in test_queries:
        print(f"\n{'=' * 70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA: {result['answer']}")
        print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")


import json
import os
import sys
from pathlib import Path

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import chromadb
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# =============================================================================
# CONFIGURATION — Giải thích lựa chọn
# =============================================================================

# Chunking Strategy:
# CHUNK_SIZE=800: Độ dài vừa đủ cho các điều khoản và bài viết chính sách TMĐT,
#   giúp giữ nguyên ngữ cảnh hoàn chỉnh của điều khoản mà không tốn quá nhiều token.
# CHUNK_OVERLAP=100: Đảm bảo các câu/ý nằm ở ranh giới cắt không bị đứt đoạn.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
CHUNKING_METHOD = "recursive"  # "recursive" | "markdown_header" | "semantic"

# Embedding Model (dùng OpenAI theo yêu cầu):
# text-embedding-3-small (1536 dim): Tốc độ cực nhanh, nhẹ, hỗ trợ tiếng Việt tuyệt vời,
#   không cần tải model local nặng 1-2GB.
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Vector Store:
# ChromaDB: Đơn giản, lưu trữ local persistent, hỗ trợ cosine similarity.
VECTOR_STORE = "chromadb"
COLLECTION_NAME = "ecommerce_support_docs"

# Mapping nhãn metadata customer_role (K4 Variant Requirement)
CUSTOMER_ROLE_MAP = {
    "returns-refund-policy-shopee.md": "both",
    "payment-methods-shopee.md": "buyer",
    "privacy-policy-shopee.md": "both",
    "article_01.md": "buyer",
    "article_02.md": "seller",
    "article_03.md": "buyer",
    "article_04.md": "both",
    "article_05.md": "both",
}


# =============================================================================
# IMPLEMENTATION
# =============================================================================

def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str, 'customer_role': str}}
    """
    documents = []
    if not STANDARDIZED_DIR.exists():
        print(f"⚠ Thư mục {STANDARDIZED_DIR} không tồn tại!")
        return documents

    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in str(md_file) else "news"
        filename = md_file.name
        
        # Gán nhãn customer_role phù hợp
        role = CUSTOMER_ROLE_MAP.get(filename)
        if not role:
            lower_content = content.lower()
            if "người bán" in lower_content and "người mua" in lower_content:
                role = "both"
            elif "người bán" in lower_content:
                role = "seller"
            else:
                role = "buyer"

        documents.append({
            "content": content,
            "metadata": {
                "source": filename,
                "type": doc_type,
                "customer_role": role
            }
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy RecursiveCharacterTextSplitter.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "customer_role": doc["metadata"].get("customer_role", "both")
                }
            })
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Hàm dùng chung để embed danh sách text (dùng cho cả Task 4 và Task 5).
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    api_key = os.getenv("OPENAI_API_KEY")

    if provider == "openai" or api_key:
        if not api_key:
            raise ValueError("OPENAI_API_KEY không được tìm thấy trong .env!")
        client = OpenAI(api_key=api_key)
        all_embeddings = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            resp = client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
            all_embeddings.extend([item.embedding for item in resp.data])
        return all_embeddings
    else:
        # Fallback local model nếu không có API key
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-m3")
        embeddings = model.encode(texts, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng OpenAI text-embedding-3-small.
    """
    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb
    return chunks


def get_collection():
    """Lấy hoặc tạo mới ChromaDB collection (dùng cho Task 5/Task 9)."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào ChromaDB vector store.
    """
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Xóa collection cũ trước khi reindex để tránh trộn lẫn vector rác
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    ids = [f"{c['metadata']['source']}_chunk_{c['metadata']['chunk_index']}" for c in chunks]
    documents = [c["content"] for c in chunks]
    embeddings = [c["embedding"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print(f"✓ Đã index {len(chunks)} chunks vào ChromaDB collection '{COLLECTION_NAME}'")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("✓ Indexed to vector store thành công!")


if __name__ == "__main__":
    run_pipeline()


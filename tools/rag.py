import os
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent
# Tải mô hình embedding từ thư mục địa phương
@lru_cache(maxsize=1)
def load_model():
    local_model_path = os.path.join("models", "Vietnamese_Embedding")
    model = SentenceTransformer(local_model_path)
    return model

@lru_cache(maxsize=1)
def connect_chroma_db():
    # Đường dẫn tới thư mục chứa file ChromaDB
    persist_dir = os.path.join("chroma_db", "chroma_db_faqs")  

    # Kết nối tới ChromaDB và lấy collection
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection("faqs_collection")
    return collection


def get_embedding(text: str) -> list[float]:
    if not text.strip():
        print("Attempted to get embedding for empty text.")
        return []

    model = load_model()
    embedding = model.encode(text)

    return embedding.tolist()

def search_project_documents(query: str):
    query_embed = get_embedding(query)
    answer = []
    collection = connect_chroma_db()
    results = collection.query(
        query_embeddings=[query_embed],  # danh sách vector truy vấn
        n_results=5  # số kết quả tối đa trả về
    )
    for doc in results["metadatas"][0]:
        answer.append(doc.get("answer_text"))
    return answer






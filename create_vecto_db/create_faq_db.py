import os
import shutil
import logging
from datetime import datetime
import json
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb
import unicodedata
import time

# Định vị thư mục log phù hợp với cấu trúc hiện tại
def setup_logger(log_dir: str = r"D:/Chatbot_Data4Life/v1/create_vecto_db/logs/logs"):
    """Khởi tạo logger để ghi lại quá trình xử lý."""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"create_faq_db_log_{timestamp}.log")

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler() 
        ]
    )
    logging.info("=== Logger initialized ===")
    return logging

# Liên kết tới mô hình embedding đã lưu trên máy
def load_embedding_model(model_path: str) -> SentenceTransformer:
    """Tải mô hình embedding từ một đường dẫn local."""
    try:
        logging.info(f"Đang tải mô hình embedding từ: {model_path}...")
        model_path = r"D:/Chatbot_Data4Life/v1/models/Vietnamese_Embedding"
        model = SentenceTransformer(model_path)
        logging.info("Tải mô hình embedding thành công.")
        return model
    except Exception as e:
        logging.error(f"Lỗi khi tải mô hình embedding: {e}")
        raise

def clear_chroma_db_folder(db_path: str, db_folder: str):
    """Xóa toàn bộ nội dung trong thư mục ChromaDB để tạo mới."""
    full_path = os.path.join(db_path, db_folder)
    if os.path.exists(full_path):
        try:
            shutil.rmtree(full_path)
            logging.info(f"Đã xóa thành công thư mục DB cũ: {full_path}")
        except Exception as e:
            logging.error(f"Không thể xóa thư mục DB {full_path}: {e}")
    os.makedirs(full_path, exist_ok=True)
    logging.info(f"Đã tạo thư mục DB mới: {full_path}")



def load_and_prepare_faq_data(csv_path: str) -> pd.DataFrame:
    """Đọc file CSV và chuẩn bị dữ liệu."""
    try:
        logging.info(f"Đang đọc dữ liệu từ: {csv_path}")
        df = pd.read_csv(csv_path)

        # Đảm bảo CSV có đủ các cột bắt buộc
        required_columns = ['id', 'title', 'answer_text']
        if not all(col in df.columns for col in required_columns):
            logging.error(f"File CSV thiếu các cột bắt buộc: {required_columns}")
            return pd.DataFrame() 

        # Loại bỏ dòng thiếu dữ liệu ở cột quan trọng
        df.dropna(subset=required_columns, inplace=True)

        # Đảm bảo 'id' là duy nhất và kiểu string
        if df['id'].duplicated().any():
            logging.warning("Phát hiện các ID trùng lặp. Giữ lại bản ghi đầu tiên.")
            df.drop_duplicates(subset=['id'], keep='first', inplace=True)
        df['id'] = df['id'].astype(str)

        # Điền 'N/A' cho metadata không bắt buộc khi thiếu
        optional_metadata_cols = ['answer_html', 'source_url']
        for col in optional_metadata_cols:
            if col in df.columns:
                df[col].fillna('N/A', inplace=True)

        logging.info(f"Đọc và chuẩn bị thành công {len(df)} bản ghi FAQ.")
        return df

    except FileNotFoundError:
        logging.error(f"Không tìm thấy file CSV tại đường dẫn: {csv_path}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Lỗi khi đọc file CSV: {e}")
        return pd.DataFrame()


def create_faq_embeddings(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    """Tạo embeddings cho một danh sách các văn bản (tiêu đề FAQ)."""
    if not texts:
        logging.warning("Không có văn bản nào để tạo embedding.")
        return []
    try:
        logging.info(f"Bắt đầu tạo embedding cho {len(texts)} tiêu đề...")
        t1 = time.time()
        # Dùng batch processing để tạo embedding nhanh hơn
        embeddings = model.encode(texts, show_progress_bar=True)
        t2 = time.time()
        logging.info(f"Hoàn thành tạo embedding trong {t2 - t1:.2f} giây.")
        return embeddings.tolist()
    except Exception as e:
        logging.error(f"Lỗi trong quá trình tạo embedding: {e}")
        return []


def store_in_chromadb(
    db_path: str,
    db_folder: str,
    collection_name: str,
    faq_df: pd.DataFrame,
    embeddings: list[list[float]]
):
    """Lưu trữ dữ liệu và embeddings vào ChromaDB."""
    try:
        full_db_path = os.path.join(db_path, db_folder)
        client = chromadb.PersistentClient(path=full_db_path)

        # Dùng get_or_create để reuse collection nếu đã có
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"} 
        )
        logging.info(f"Sử dụng/Tạo collection '{collection_name}' tại '{full_db_path}'")

        # Chuẩn bị ids, documents, metadata cho ChromaDB
        ids = faq_df["id"].tolist()
        documents = faq_df["title"].tolist() 
        metadatas = faq_df.to_dict(orient='records') 

        # Upsert để thay thế hoặc thêm theo id
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        logging.info(f"Đã thêm/cập nhật thành công {len(ids)} bản ghi vào collection.")
        logging.info(f"Tổng số bản ghi trong collection hiện tại: {collection.count()}")

    except Exception as e:
        logging.error(f"Lỗi khi lưu trữ vào ChromaDB: {e}")


if __name__ == "__main__":
    # Khởi tạo logger trước khi bắt đầu xử lý
    logger = setup_logger()

    # Đảm bảo đường dẫn config tương ứng với môi trường
    try:
        CONFIG_PATH = "D:/Chatbot_Data4Life/v1/create_vecto_db/config.json"
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Không tìm thấy file config.json. Vui lòng tạo file này.")
        exit()

    # Đọc tham số từ config
    FAQ_CSV_PATH = config["faq_csv_path"]
    DB_PATH = config["db_path"]
    DB_FOLDER = config["db_folder"]
    COLLECTION_NAME = config["collection_name"]
    LOCAL_MODEL_PATH = config["local_model_path"]

    # Tải dữ liệu FAQ từ file CSV
    faq_dataframe = load_and_prepare_faq_data(FAQ_CSV_PATH)

    if faq_dataframe.empty:
        logger.error("Không có dữ liệu để xử lý. Dừng chương trình.")
    else:
        model = load_embedding_model(LOCAL_MODEL_PATH)

        # Tạo embedding cho mỗi tiêu đề FAQ
        titles_to_embed = faq_dataframe['title'].tolist()
        faq_embeddings = create_faq_embeddings(model, titles_to_embed)

        if faq_embeddings:
            store_in_chromadb(
                db_path=DB_PATH,
                db_folder=DB_FOLDER,
                collection_name=COLLECTION_NAME,
                faq_df=faq_dataframe,
                embeddings=faq_embeddings
            )
            logger.info("=== QUÁ TRÌNH TẠO VECTOR DB HOÀN TẤT ===")
        else:
            logger.error("Không thể tạo embeddings. Dừng quá trình lưu vào DB.")

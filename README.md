# Chatbot hỗ trợ Data4Life

## 1. Tổng quan
Dự án này là một chatbot hỗ trợ dựa trên kiến trúc multi-role agent: frontend Streamlit cho tương tác người dùng, backend FastAPI để điều phối workflow qua LangGraph, và các thành phần bổ trợ giúp truy vấn tài liệu nội bộ và lưu lịch sử vào SQL Server.

## 2. Thành phần chính
- **`app.py` + `style.css`**: giao diện Streamlit. `app.py` gọi `POST /chat` và `GET /sessions` từ backend, hiển thị lịch sử chat và cho phép tạo cuộc trò chuyện mới; `style.css` điều chỉnh padding và kiểu nút để phù hợp với thiết kế riêng.
- **`api.py`**: FastAPI. Khởi tạo `MultiRoleAgentGraph`, phục vụ các endpoint `/sessions`, `/history/{session_id}` và `/chat`, đồng thời gọi `log_to_database_internal` để ghi cả cuộc hội thoại và metadata LLM vào SQL Server.
- **`agent_core/`**: pipeline LangGraph. `graph.py` định nghĩa chuỗi node, `node.py` thực hiện các bước: nạp prompt từ `prompt/General_Prompt.docx`, đọc cấu hình tool từ `prompt/tool.yaml`, lấy summary memory, gọi Gemini Analyzer để xác định tool cần dùng, thực thi tool (qua `tools/tool_registry.py`) và tổng hợp câu trả lời với Gemini Synthesizer.
- **`tools/`**: bao gồm `rag.py` (SentenceTransformers bilingual, ChromaDB persistent client) và `tool_registry.py` để ánh xạ tên tool như `search_project_documents`.
- **`utils/llm_wrapper.py`**: wrapper gọi các model Gemini (Analyzer, Synthesizer, Summarizer) thông qua thư viện `google.generativeai`. Mỗi lớp yêu cầu một biến môi trường API key riêng `GOOGLE_API_KEY_1`, `_2`, `_3`.
- **`connect_SQL/config.json` + `connect_SQL/connect_SQL.py`**: cấu hình kết nối SQL Server (server, database, user, password). Compose mount file này vào container backend.
- **`chroma_db/chroma_db_faqs`**: folder chứa dữ liệu ChromaDB (Chroma sqlite). Dữ liệu bạn cần có thể xây dựng lại với `create_vecto_db/create_faq_db.py`.

## 3. Cài đặt và cấu hình
1. Cài Python 3.10.x, tạo virtualenv và `pip install -r requirements.txt` (file hiện tại có encoding Windows, hãy đảm bảo nó dùng UTF-8 trước khi cài).
2. Chuẩn bị các biến môi trường:
   - `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, `GOOGLE_API_KEY_3` (Gemini Analyzer, Synthesizer, Summarizer).
   - `API_URL` để frontend biết backend, mặc định `http://localhost:8000`.
3. Cập nhật `connect_SQL/config.json` với thông tin SQL Server (driver `ODBC Driver 17 for SQL Server`).
4. Mô hình embedding: thư mục `models/Vietnamese_Embedding` phải có SentenceTransformer đã huấn luyện; có thể lấy từ bản sao của `create_vecto_db` khi đổi đường dẫn tương ứng.
5. Tạo vector DB FAQ bằng cách chỉnh `create_vecto_db/config.json`, chạy `python create_vecto_db/create_faq_db.py` để ghi dữ liệu vào `chroma_db/chroma_db_faqs`.

## 4. Khởi chạy bản local (không dùng Docker)
1. Khởi server backend: `uvicorn api:app --reload --host 0.0.0.0 --port 8000`.
2. Trong terminal khác, khởi frontend Streamlit: `streamlit run app.py --server.port 8501`.
3. Mở `http://localhost:8501` để tương tác chatbot. Nếu bạn bật `API_URL` khác, cập nhật biến cùng lúc cả backend và frontend.

## 5. Chạy bằng Docker Compose
1. Thêm `.env` chứa các API keys và `API_URL` nếu cần; backend lấy `connect_SQL/config.json` và `models/` qua bind mount.
2. Chạy `docker compose up --build`. Compose tạo hai container: `backend-api` (uvicorn 8000) và `frontend-ui` (Streamlit 8501).
3. Nếu cần rebuild vector DB, thực thi script `create_vecto_db/create_faq_db.py` trước khi bắn container (hoặc mount `chroma_db`).

## 6. Phát triển và mở rộng
- Cập nhật prompt: chỉnh `prompt/General_Prompt.docx` để thay đổi giọng nói vai trò; chỉnh `prompt/tool.yaml` để thêm tool-desc mới và đồng thời đăng ký trong `tools/tool_registry.py`.
- Tool mới nên trả dữ liệu dạng JSON/metadata để node `llm_response` có thể nhúng vào prompt tổng hợp.
- Đọc `agent_core/node.py` để hiểu cách `TaskAnalyzer` trích JSON `required_tools`, thực thi và truyền `tool_results` cho LLM cuối cùng.

## 7. Khó khăn thường gặp
- `Gemini` trả JSON không đúng schema → kiểm tra bước `_extract_json_from_text` trong `agent_core/node.py` và log lại output thô.
- SQL connection fail → xác minh lại `connect_SQL/config.json` và đảm bảo driver ODBC được cài (`Dockerfile` đã làm điều đó).`
- Frontend không cập nhật session cũ → backend `/history/{session_id}` trả lại chuỗi user/assistant đã lưu.

## 8. Checklist trước khi deploy
- [ ] `.env` chứa đủ 3 key Gemini và `API_URL`.
- [ ] `connect_SQL/config.json` chính xác.
- [ ] `models/Vietnamese_Embedding` và `chroma_db/chroma_db_faqs` tồn tại.
- [ ] `requirements.txt` định dạng UTF-8.

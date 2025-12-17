# =========================
# JOB PORTAL AI - 1 FILE
# =========================
# Mô tả:
# - AI matching 2 chiều: Ứng viên <-> Nhà tuyển dụng
# - Chatbot đọc profile từ DB để cá nhân hóa
# - Embedding + FAISS + LLM (giả lập)
# =========================

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
# --- Cấu hình model và đường dẫn ---
EMBEDDING_MODEL_NAME = "keepitreal/vietnamese-sbert"

# =========================
# 1. Khởi tạo app
# =========================
app = FastAPI(title="Job Portal AI (Demo)")

# =========================
# 2. Fake Database (demo)
# =========================
USERS_DB = {
    "u1": {
        "role": "candidate",
        "name": "Nguyễn Văn A",
        "skills": ["Java", "Spring Boot", "MySQL"],
        "experience": 2,
        "location": "TP Hồ Chí Minh"
    },
    "u2": {
        "role": "recruiter",
        "company": "ABC Tech",
        "job_title": "Backend Developer",
        "requirements": ["Java", "Spring Boot", "Docker"],
        "location": "TP Hồ Chí Minh"
    },
    "u3": {
        "role": "recruiter",
        "company": "XYZ Solutions",
        "job_title": "Java Developer",
        "requirements": ["Java", "MySQL"],
        "location": "Hà Nội"
    }
}

# =========================
# 3. Embedding model
# =========================
# --- Load Embedding Model ---
print("Đang tải Embedding model...")
try:
  embedding_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_NAME,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
  )
  print("Embedding model đã tải.")
except Exception as e:
  print(f"Lỗi nghiêm trọng khi tải Embedding model: {e}")
  embedding_model = None
  exit()

# =========================
# 4. Chuẩn hóa profile -> text
# =========================
def profile_to_text(profile: Dict) -> str:
    if profile["role"] == "candidate":
        return (
            f"Candidate with skills {', '.join(profile['skills'])}, "
            f"{profile['experience']} years experience, "
            f"location {profile['location']}"
        )
    else:
        return (
            f"Job {profile['job_title']} requires "
            f"{', '.join(profile['requirements'])}, "
            f"location {profile['location']}"
        )

# =========================
# 5. Tạo FAISS index
# =========================
documents = []
for user_id, profile in USERS_DB.items():
    documents.append(
        Document(
            page_content=profile_to_text(profile),
            metadata={
                "user_id": user_id,
                "role": profile["role"]
            }
        )
    )

import os

INDEX_PATH = "faiss_index"

if os.path.exists(INDEX_PATH):
    vector_store = FAISS.load_local(
        INDEX_PATH,
        embedding_model,
        allow_dangerous_deserialization=True
    )
else:
    vector_store = FAISS.from_documents(documents, embedding_model)
    vector_store.save_local(INDEX_PATH)
    print(f"Đã tạo và lưu FAISS index vào '{vector_store}'.")

# =========================
# 6. Matching Engine (2 chiều)
# =========================
def find_matches(user_id: str, k: int = 3):
    user_profile = USERS_DB[user_id]
    query_text = profile_to_text(user_profile)

    results = vector_store.similarity_search(query_text, k=k + 1)

    matches = []
    for doc in results:
        match_id = doc.metadata["user_id"]
        if match_id != user_id:
            matches.append({
                "id": match_id,
                "role": doc.metadata["role"],
                "profile": USERS_DB[match_id]
            })
    return matches

# =========================
# 7. Request model
# =========================
class ChatRequest(BaseModel):
    user_id: str
    question: str

# =========================
# 8. Chatbot cá nhân hóa
# =========================
@app.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    question = req.question

    if user_id not in USERS_DB:
        return {"answer": "Không tìm thấy người dùng."}

    profile = USERS_DB[user_id]
    matches = find_matches(user_id)

    # Giả lập LLM (để dễ nộp bài)
    if profile["role"] == "candidate":
        answer = (
            f"Chào {profile['name']}, dựa trên kỹ năng "
            f"{', '.join(profile['skills'])} và {profile['experience']} năm kinh nghiệm, "
            f"bạn phù hợp với các vị trí sau:\n"
        )
        for m in matches:
            answer += f"- {m['profile']['job_title']} tại {m['profile']['company']}\n"
    else:
        answer = (
            f"Dựa trên yêu cầu tuyển dụng của bạn, hệ thống tìm thấy "
            f"{len(matches)} ứng viên phù hợp:\n"
        )
        for m in matches:
            answer += f"- {m['profile']['name']} ({', '.join(m['profile']['skills'])})\n"

    return {
        "question": question,
        "answer": answer,
        "personalized": True
    }

# =========================
# 9. Run server
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

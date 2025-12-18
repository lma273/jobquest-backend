import io
import os
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from openai import OpenAI

app = FastAPI(title="JobQuest AI Backend")

# --- 1. CẤU HÌNH CORS (Để Frontend React gọi được) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong production nên đổi thành domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. KẾT NỐI MONGODB ATLAS (DỮ LIỆU THẬT) ---
MONGO_URI = "mongodb+srv://jobquest:23020510@mal.wjbixqu.mongodb.net/?appName=mal"
DB_NAME = "ptud" # Mặc định Atlas hay dùng 'test', bạn có thể đổi thành tên DB thật nếu khác
COLLECTION_JOBS = "jobs"

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    jobs_collection = db[COLLECTION_JOBS]
    print("✅ Đã kết nối tới MongoDB Atlas!")
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")

# --- 3. CẤU HÌNH AI (OpenRouter) ---
OPENROUTER_API_KEY = "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"
client_llm = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

# Load Model Embeddings (Chỉ dùng nếu cần Search Vector, ở feature này chưa cần lắm)
# model = SentenceTransformer('all-MiniLM-L6-v2') 

# --- HELPER: Đọc PDF ---
async def extract_text_from_pdf(file: UploadFile):
    try:
        content = await file.read()
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Lỗi đọc PDF: {e}")
        return ""

# --- API 1: PHÂN TÍCH TRỰC TIẾP KHI NỘP ĐƠN (QUAN TRỌNG NHẤT) ---
@app.post("/analyze_application")
async def analyze_application(
    resume: UploadFile = File(...),      # Nhận file PDF từ form
    job_context: str = Form(...),        # Nhận thông tin Job (Title, Desc...) dạng chuỗi
    user_question: str = Form(default="Phân tích mức độ phù hợp") # Câu hỏi tùy chọn
):
    """
    API này nhận File CV và thông tin Job từ Frontend gửi lên (FormData).
    Nó đọc CV, so sánh với Job và trả về lời tư vấn.
    """
    
    # 1. Đọc nội dung CV từ file PDF vừa upload
    cv_text = await extract_text_from_pdf(resume)
    
    if len(cv_text) < 50:
        return {"response": "⚠️ File CV quá ngắn hoặc không đọc được nội dung text. Hãy thử file khác."}

    # 2. Chuẩn bị Prompt cho AI
    system_prompt = """
    Bạn là chuyên gia tuyển dụng (HR Senior). 
    Nhiệm vụ: Đánh giá sự phù hợp của ứng viên dựa trên CV và JD được cung cấp.
    Phong cách: Ngắn gọn, súc tích, đi thẳng vào vấn đề. Chỉ ra điểm mạnh và điểm yếu (Gap Analysis).
    """
    
    user_prompt = f"""
    --- THÔNG TIN CÔNG VIỆC (JOB DESCRIPTION) ---
    {job_context}
    
    --- NỘI DUNG CV ỨNG VIÊN ---
    {cv_text[:2000]} (Đã cắt gọn)
    
    --- YÊU CẦU ---
    {user_question}
    
    Hãy trả lời bằng tiếng Việt.
    """

    # 3. Gọi AI Phân tích
    try:
        completion = client_llm.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free", # Hoặc model khác tùy bạn chọn
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600
        )
        ai_response = completion.choices[0].message.content
        
        return {
            "success": True,
            "cv_preview": cv_text[:200] + "...", # Trả về 1 chút nội dung để debug
            "ai_analysis": ai_response
        }

    except Exception as e:
        return {"success": False, "response": f"Lỗi gọi AI: {str(e)}"}

# --- API 2: LẤY DANH SÁCH JOB TỪ MONGODB (KHÔNG GIẢ LẬP) ---
@app.get("/jobs")
async def get_real_jobs():
    """
    Lấy danh sách Job thật từ MongoDB Atlas để hiển thị lên Frontend (nếu cần).
    """
    try:
        # Lấy 50 job mới nhất
        jobs_cursor = jobs_collection.find().sort("postedAt", -1).limit(50)
        jobs = []
        for job in jobs_cursor:
            # Convert ObjectId thành string để không bị lỗi JSON
            job["id"] = str(job.pop("_id"))
            jobs.append(job)
        
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Cập nhật Data Model (Thêm mode có default value để không lỗi frontend) ---
class ConsultRequest(BaseModel):
    cv_text: str
    job_context: str
    user_question: str
    mode: str = "candidate"  # Mặc định là ứng viên nếu frontend không gửi

# --- API 4: CHATBOT CONSULTANT (ĐÃ SỬA LOGIC THẬT) ---
@app.post("/consult")
async def ai_consultant(req: ConsultRequest):
    """
    API tư vấn nghề nghiệp thông minh.
    Nhận: Text CV, Ngữ cảnh Job, Câu hỏi.
    Trả về: Lời khuyên từ AI.
    """
    
    # 1. Chọn vai trò (Persona) cho AI
    if req.mode == "candidate":
        system_prompt = """
        Bạn là Chuyên gia Tư vấn Nghề nghiệp (Career Coach) tận tâm và sắc sảo.
        Nhiệm vụ: Phân tích mức độ phù hợp giữa Hồ sơ năng lực (CV) và Mô tả công việc (JD).
        Phong cách:
        - Trả lời ngắn gọn, súc tích (dưới 300 từ).
        - Giọng điệu khích lệ nhưng trung thực.
        - Chỉ rõ các kỹ năng còn thiếu (Skill Gap) nếu có.
        - Đưa ra lời khuyên phỏng vấn cụ thể.
        """
    else:
        # Dành cho tương lai nếu bạn làm tính năng cho Recruiter
        system_prompt = """
        Bạn là Trợ lý Tuyển dụng (HR Assistant).
        Nhiệm vụ: Đánh giá nhanh ứng viên này có tiềm năng không.
        Phong cách: Khách quan, tập trung vào rủi ro và đánh giá năng lực cốt lõi.
        """

    # 2. Tạo ngữ cảnh (Context) để gửi cho AI
    # Kết hợp thông tin Job, CV và câu hỏi người dùng
    user_prompt = f"""
    === THÔNG TIN CÔNG VIỆC (JD) ===
    {req.job_context}
    
    === HỒ SƠ ỨNG VIÊN (CV) ===
    {req.cv_text[:3000]}  # Giới hạn 3000 ký tự để tiết kiệm token
    
    === CÂU HỎI CỦA NGƯỜI DÙNG ===
    "{req.user_question}"
    
    Hãy trả lời câu hỏi trên bằng tiếng Việt.
    """

    try:
        # 3. Gọi OpenRouter (AI Model)
        completion = client_llm.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free", # Model miễn phí và rất thông minh
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800, # Độ dài câu trả lời tối đa
            temperature=0.7 # Độ sáng tạo (0.7 là mức cân bằng)
        )
        
        # 4. Trả kết quả về Frontend
        return {"response": completion.choices[0].message.content}
    
    except Exception as e:
        print(f"Lỗi AI: {str(e)}")
        return {"response": "Xin lỗi, hệ thống AI đang bận. Bạn vui lòng thử lại sau giây lát."}
# Run server: uvicorn chatbot:app --reload
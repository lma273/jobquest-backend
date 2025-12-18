# """
# AI Job Consultant System - FastAPI Chatbot
# Kết hợp MongoDB (lưu trữ) + Qdrant (Vector Search)
# Chạy riêm trên port 8001
# """
# import io
# import uuid
# from typing import List, Optional
# from datetime import datetime
# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from pymongo import MongoClient
# from pymongo.errors import ConnectionFailure
# from qdrant_client import QdrantClient
# from qdrant_client.models import Distance, VectorParams, PointStruct
# from sentence_transformers import SentenceTransformer
# from pypdf import PdfReader
# from openai import OpenAI
# import os
# from dotenv import load_dotenv
# from bson import ObjectId

# load_dotenv()

# app = FastAPI(title="AI Job Consultant System")

# # ✅ CORS cho phép Frontend gọi từ localhost:5173
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # --- 1. CẤU HÌNH HỆ THỐNG ---
# print("⏳ Loading AI Model...")
# model = SentenceTransformer('all-MiniLM-L6-v2')

# # 🗄️ KẾT NỐI MONGODB
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# MONGO_DB = os.getenv("MONGO_DB", "jobquest")
# MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "jobs")

# try:
#     mongo_client = MongoClient(MONGO_URI)
#     mongo_client.admin.command('ping')  # Test connection
#     db = mongo_client[MONGO_DB]
#     jobs_collection = db[MONGO_COLLECTION]
#     print(f"✅ Kết nối MongoDB thành công: {MONGO_URI}")
# except ConnectionFailure:
#     print(f"❌ Không thể kết nối MongoDB: {MONGO_URI}")
#     raise

# # 🔌 KẾT NỐI QDRANT
# QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
# QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
# QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "jobs_db_v2")

# client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)

# # Đảm bảo collection tồn tại
# if not client.collection_exists(QDRANT_COLLECTION):
#     client.create_collection(
#         collection_name=QDRANT_COLLECTION,
#         vectors_config=VectorParams(size=384, distance=Distance.COSINE),
#     )
#     print(f"✅ Tạo Qdrant collection '{QDRANT_COLLECTION}' thành công")
# else:
#     print(f"✅ Qdrant collection '{QDRANT_COLLECTION}' đã tồn tại")

# # 🔑 API Key từ env
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# if not OPENROUTER_API_KEY:
#     raise ValueError("⚠️ Thiếu OPENROUTER_API_KEY trong .env")

# client_llm = OpenAI(
#     base_url="https://openrouter.ai/api/v1",
#     api_key=OPENROUTER_API_KEY,
# )

# # --- DATA MODELS ---
# class JobItem(BaseModel):
#     title: str
#     desc: str
#     requirements: str

# class ConsultRequest(BaseModel):
#     cv_text: str
#     job_context: str
#     user_question: str
#     mode: str = "candidate"  # "candidate" hoặc "recruiter"

# class JDRequest(BaseModel):
#     keywords: str

# # --- HELPER FUNCTIONS ---

# def _generate_vector(text: str):
#     """Generate vector từ text"""
#     return model.encode(text).tolist()

# def _job_dict_to_qdrant_payload(job_doc):
#     """Convert MongoDB job doc thành Qdrant payload"""
#     return {
#         "title": job_doc.get("title", ""),
#         "company": job_doc.get("company", ""),
#         "created_at": str(job_doc.get("created_at", ""))
#     }

# def _create_combined_text(job_doc):
#     """Tạo text ghép để vector hóa"""
#     return f"{job_doc['title']}. {job_doc['desc']}. Yêu cầu: {job_doc['requirements']}"

# # --- API 1: RESET & TẠO DỮ LIỆU MẦU ---
# @app.post("/reset_db")
# async def reset_database():
#     """Xóa MongoDB + Qdrant cũ, tạo lại với dữ liệu mẫu"""
    
#     # Xóa data cũ
#     jobs_collection.delete_many({})
#     if client.collection_exists(QDRANT_COLLECTION):
#         client.delete_collection(QDRANT_COLLECTION)
    
#     # Tạo lại Qdrant collection
#     client.create_collection(
#         collection_name=QDRANT_COLLECTION,
#         vectors_config=VectorParams(size=384, distance=Distance.COSINE),
#     )

#     # Dữ liệu mẫu
#     fake_jobs = [
#         {
#             "title": "DevOps Intern", 
#             "company": "Tech Corp Vietnam",
#             "desc": "Hỗ trợ vận hành hệ thống CI/CD, monitor server.", 
#             "requirements": "Yêu cầu cơ bản về Linux, Docker. Biết về Kubernetes là điểm cộng lớn. Tư duy automation."
#         },
#         {
#             "title": "Senior Python Backend", 
#             "company": "StartupXYZ",
#             "desc": "Phát triển Microservices hiệu năng cao.", 
#             "requirements": "5 năm kinh nghiệm Python, FastAPI, PostgreSQL. Có kinh nghiệm System Design và AWS."
#         },
#         {
#             "title": "React Frontend Developer", 
#             "company": "WebAgency Pro",
#             "desc": "Xây dựng giao diện người dùng mượt mà.", 
#             "requirements": "Thành thạo ReactJS, TailwindCSS, Redux. Có mắt thẩm mỹ và biết dùng Figma."
#         },
#         {
#             "title": "UI/UX Designer",
#             "company": "DesignStudio",
#             "desc": "Thiết kế giao diện cho mobile app và web.",
#             "requirements": "2+ năm kinh nghiệm Figma, Sketch. Portfolio ấn tượng. Có vốn tiếng Anh tốt."
#         },
#         {
#             "title": "Data Analyst",
#             "company": "FinTech Solutions",
#             "desc": "Phân tích dữ liệu và tạo báo cáo cho management.",
#             "requirements": "Excel nâng cao, SQL, Power BI. Thích làm việc với số liệu. Tư duy logic."
#         }
#     ]
    
#     # Insert vào MongoDB
#     result = jobs_collection.insert_many([
#         {**job, "created_at": datetime.now()} for job in fake_jobs
#     ])
    
#     # Tạo vector và lưu vào Qdrant
#     qdrant_points = []
#     for i, job in enumerate(fake_jobs):
#         combined_text = _create_combined_text(job)
#         vector = _generate_vector(combined_text)
        
#         # Dùng MongoDB ObjectId làm Qdrant point id
#         point_id = str(result.inserted_ids[i])
        
#         qdrant_points.append(PointStruct(
#             id=point_id,
#             vector=vector,
#             payload=_job_dict_to_qdrant_payload(job)
#         ))
    
#     client.upsert(collection_name=QDRANT_COLLECTION, points=qdrant_points)
    
#     return {
#         "message": "✅ Đã reset DB (MongoDB + Qdrant) và tạo dữ liệu mẫu!",
#         "jobs_created": len(result.inserted_ids)
#     }

# # --- API 2: NHÀ TUYỂN DỤNG ĐĂNG BÀI MỚI ---
# @app.post("/post_job")
# async def post_job(job: JobItem):
#     """Thêm job mới vào MongoDB + Qdrant"""
    
#     try:
#         # 1. Lưu vào MongoDB
#         job_doc = {
#             **job.dict(),
#             "created_at": datetime.now(),
#             "company": "Công ty của tôi"  # TODO: Lấy từ recruiter profile
#         }
#         result = jobs_collection.insert_one(job_doc)
#         job_id = str(result.inserted_id)
        
#         # 2. Generate vector
#         combined_text = _create_combined_text(job_doc)
#         vector = _generate_vector(combined_text)
        
#         # 3. Lưu vào Qdrant (ref MongoDB _id)
#         point = PointStruct(
#             id=job_id,
#             vector=vector,
#             payload=_job_dict_to_qdrant_payload(job_doc)
#         )
#         client.upsert(collection_name=QDRANT_COLLECTION, points=[point])
        
#         return {
#             "message": "✅ Đăng tin tuyển dụng thành công!",
#             "job_id": job_id,
#             "job_title": job.title
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Lỗi khi đăng job: {str(e)}")

# # --- API 3: ỨNG VIÊN TÌM VIỆC (MATCHING) ---
# @app.post("/find_matches")
# async def find_matches(file: UploadFile = File(...)):
#     """Đọc PDF CV và tìm job phù hợp"""
#     try:
#         # 1. Đọc PDF
#         content = await file.read()
#         reader = PdfReader(io.BytesIO(content))
#         cv_text = ""
#         for page in reader.pages:
#             cv_text += page.extract_text()
        
#         # 2. Vector Search trong Qdrant
#         cv_vector = _generate_vector(cv_text)
#         hits = client.query_points(
#             collection_name=QDRANT_COLLECTION,
#             query=cv_vector,
#             limit=5,
#         ).points

#         # 3. Lấy full details từ MongoDB dùng Qdrant point IDs
#         results = []
#         for hit in hits:
#             # hit.id là MongoDB ObjectId (dưới dạng string)
#             try:
#                 job_doc = jobs_collection.find_one({"_id": ObjectId(hit.id)})
#                 if job_doc:
#                     results.append({
#                         "id": hit.id,
#                         "score": round(hit.score, 4),
#                         "data": {
#                             "title": job_doc.get("title"),
#                             "company": job_doc.get("company"),
#                             "desc": job_doc.get("desc"),
#                             "requirements": job_doc.get("requirements"),
#                             "created_at": str(job_doc.get("created_at"))
#                         }
#                     })
#             except Exception as e:
#                 print(f"⚠️ Lỗi lấy job {hit.id}: {str(e)}")
#                 continue

#         return {
#             "cv_text": cv_text,
#             "matches": results,
#             "total_matches": len(results)
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Lỗi đọc PDF: {str(e)}")

# # --- API 4: CHATBOT CONSULTANT (TƯ VẤN VIÊN AI) ---
# @app.post("/consult")
# async def ai_consultant(req: ConsultRequest):
#     """
#     Chatbot tư vấn dựa trên ngữ cảnh
#     """
    
#     if req.mode == "candidate":
#         system_prompt = """
#         Bạn là Chuyên gia Tư vấn Nghề nghiệp (Career Coach) tận tâm.
#         Nhiệm vụ: Giúp ứng viên hiểu rõ sự phù hợp giữa CV và Job.
#         Phong cách: Khích lệ nhưng trung thực. Chỉ ra những kỹ năng còn thiếu (Gap Analysis).
#         Trả lời bằng tiếng Việt, ngắn gọn, không quá 200 từ.
#         """
#     else:
#         system_prompt = """
#         Bạn là Trợ lý Tuyển dụng (HR Assistant) sắc sảo.
#         Nhiệm vụ: Giúp nhà tuyển dụng đánh giá ứng viên.
#         Phong cách: Khách quan, tập trung vào rủi ro và năng lực.
#         Trả lời bằng tiếng Việt, ngắn gọn, không quá 200 từ.
#         """

#     user_prompt = f"""
#     --- THÔNG TIN CÔNG VIỆC (JD) ---
#     {req.job_context}
    
#     --- HỒ SƠ ỨNG VIÊN (CV) ---
#     {req.cv_text[:1500]} (đã rút gọn)
    
#     --- CÂU HỎI CỦA NGƯỜI DÙNG ---
#     "{req.user_question}"
    
#     Hãy trả lời câu hỏi trên bằng tiếng Việt, ngắn gọn, đi thẳng vào vấn đề.
#     """

#     try:
#         completion = client_llm.chat.completions.create(
#             model="meta-llama/llama-3.3-70b-instruct:free",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt}
#             ],
#             max_tokens=500
#         )
#         return {"response": completion.choices[0].message.content}
    
#     except Exception as e:
#         return {"response": f"❌ Xin lỗi, AI đang bận: {str(e)}", "error": True}

# # --- API 5: XEM TẤT CẢ JOB ---
# @app.get("/list_jobs")
# async def list_all_jobs():
#     """Lấy danh sách tất cả job từ MongoDB"""
#     try:
#         jobs = list(jobs_collection.find({}, {"_id": 1, "title": 1, "company": 1, "desc": 1, "requirements": 1, "created_at": 1}))
        
#         # Convert ObjectId to string
#         for job in jobs:
#             job["_id"] = str(job["_id"])
#             job["created_at"] = str(job.get("created_at", ""))
        
#         return {
#             "total": len(jobs),
#             "jobs": jobs
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

# # --- API 6: GENERATE JD TỰ ĐỘNG ---
# @app.post("/generate_jd")
# async def generate_jd_ai(req: JDRequest):
#     """AI giúp Nhà tuyển dụng viết JD từ vài từ khóa"""
#     prompt = f"""
#     Bạn là chuyên gia nhân sự (HR Manager).
#     Hãy viết một bản Mô tả công việc (JD) chuyên nghiệp, hấp dẫn dựa trên:
#     "{req.keywords}"
    
#     Cấu trúc:
#     1. Tiêu đề công việc (Hấp dẫn)
#     2. Mô tả công việc (3-5 gạch đầu dòng)
#     3. Yêu cầu (Kỹ năng)
#     4. Quyền lợi
    
#     Viết bằng tiếng Việt, ngắn gọn.
#     """
    
#     try:
#         completion = client_llm.chat.completions.create(
#             model="meta-llama/llama-3.3-70b-instruct:free",
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=800
#         )
#         return {"jd_content": completion.choices[0].message.content}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # --- API 7: DELETE JOB (xóa từ cả 2 database) ---
# @app.delete("/jobs/{job_id}")
# async def delete_job(job_id: str):
#     """Xóa job từ MongoDB và Qdrant"""
#     try:
#         # Xóa từ MongoDB
#         result = jobs_collection.delete_one({"_id": ObjectId(job_id)})
        
#         # Xóa từ Qdrant
#         client.delete(collection_name=QDRANT_COLLECTION, points_selector=job_id)
        
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="Job không tìm thấy")
        
#         return {"message": f"✅ Đã xóa job {job_id}"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # --- HEALTH CHECK ---
# @app.get("/health")
# async def health():
#     try:
#         # Check MongoDB
#         mongo_client.admin.command('ping')
#         mongo_status = "✅"
#     except:
#         mongo_status = "❌"
    
#     try:
#         # Check Qdrant
#         client.get_collections()
#         qdrant_status = "✅"
#     except:
#         qdrant_status = "❌"
    
#     return {
#         "status": "✅ Chatbot API running on port 8001",
#         "mongodb": mongo_status,
#         "qdrant": qdrant_status
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)


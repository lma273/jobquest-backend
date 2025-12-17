import uuid
import os
import json
import time
import asyncio
import functools
import requests
from typing import Optional, Dict, List, Union
from functools import lru_cache

import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document as LangchainDocument
import uvicorn

# --- Khởi tạo ứng dụng FastAPI ---
app = FastAPI(title="API Chatbot Hẹn Hò")

# --- Cấu hình CORS ---
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# --- Cấu hình model và đường dẫn ---
EMBEDDING_MODEL_NAME = "keepitreal/vietnamese-sbert"
FAISS_INDEX_PATH = "faiss_final"
DATA_FILE = "chat_suggestion_res.txt"

# --- Cấu hình OpenRouter ---
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"  # Có thể thay bằng mô hình khác từ OpenRouter

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

# --- Hàm tạo FAISS index ---
def create_faiss_index(file_path=DATA_FILE, vector_store_path=FAISS_INDEX_PATH):
  """Tạo và lưu FAISS index từ file dữ liệu."""
  if embedding_model is None:
    print("Lỗi: Embedding model chưa được khởi tạo.")
    return None
  if not os.path.exists(file_path):
    print(f"Lỗi: File dữ liệu '{file_path}' không tồn tại.")
    return None

  print(f"Bắt đầu tạo FAISS index từ '{file_path}'...")
  try:
    with open(file_path, "r", encoding="utf-8") as f:
      raw_text = f.read().strip().split("\n\n")

    documents = []
    current_category = "unknown"
    for chunk in raw_text:
      chunk_strip = chunk.strip()
      if chunk_strip:
        if chunk_strip.startswith("[") and chunk_strip.endswith("]"):
          current_category = chunk_strip[1:-1].strip()
          print(f"Debug: Found category: {current_category}")
        else:
          lines = [line.strip() for line in chunk_strip.split("\n") if line.strip()]
          i = 0
          while i < len(lines) - 1:
            if lines[i].startswith("Q:") and lines[i + 1].startswith("A:"):
              question = lines[i][2:].strip()
              answer = lines[i + 1][2:].strip()
              if question and answer:
                documents.append(LangchainDocument(
                  page_content=question,
                  metadata={"answer": answer, "category": current_category}
                ))
              i += 2
            else:
              i += 1

    if not documents:
      print("Không tìm thấy cặp Q/A hợp lệ nào trong file dữ liệu.")
      return None

    print(f"Đang tạo vector store với {len(documents)} tài liệu...")
    vector_store = FAISS.from_documents(documents, embedding_model)
    vector_store.save_local(vector_store_path)
    print(f"Đã tạo và lưu FAISS index vào '{vector_store_path}'.")
    return vector_store
  except Exception as e:
    print(f"Lỗi trong quá trình tạo FAISS index: {e}")
    return None

# --- Load FAISS Index ---
if os.path.exists(FAISS_INDEX_PATH) and embedding_model:
  print(f"Đang tải FAISS index từ {FAISS_INDEX_PATH}...")
  try:
    KNOWLEDGE_VECTOR_DATABASE = FAISS.load_local(
      FAISS_INDEX_PATH,
      embeddings=embedding_model,
      allow_dangerous_deserialization=True
    )
    print("FAISS index đã tải.")
  except Exception as e:
    print(f"Lỗi khi tải FAISS index: {e}. Thử tạo lại index...")
    KNOWLEDGE_VECTOR_DATABASE = create_faiss_index(DATA_FILE, FAISS_INDEX_PATH)
    if KNOWLEDGE_VECTOR_DATABASE is None:
      print("Lỗi nghiêm trọng: Không thể tải hoặc tạo FAISS index.")
      exit()
elif embedding_model:
  print(f"FAISS index tại '{FAISS_INDEX_PATH}' không tồn tại. Bắt đầu tạo mới...")
  KNOWLEDGE_VECTOR_DATABASE = create_faiss_index(DATA_FILE, FAISS_INDEX_PATH)
  if KNOWLEDGE_VECTOR_DATABASE is None:
    print("Lỗi nghiêm trọng: Không thể tạo FAISS index.")
    exit()
else:
  print("Lỗi nghiêm trọng: Embedding model không tải được, không thể tiếp tục.")
  exit()

# --- Khởi tạo OpenRouter Client ---
print("Đang khởi tạo OpenRouter client...")
try:
  client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
  )

  # Định nghĩa READER_LLM và EXTRACT_LLM
  def READER_LLM(prompt: str) -> List[Dict[str, str]]:
    try:
      response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
          {"role": "system", "content": "Bạn là trợ lý hỗ trợ giao tiếp hẹn hò."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        top_p=0.8,
        max_tokens=200,
        frequency_penalty=1.2,
      )
      return [{"generated_text": response.choices[0].message.content.strip()}]
    except Exception as e:
      print(f"Lỗi khi gọi READER_LLM qua OpenRouter: {e}")
      return []

  def EXTRACT_LLM(prompt: str) -> List[Dict[str, str]]:
    try:
      response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
          {"role": "system", "content": "Bạn là trợ lý trích xuất thông tin."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=100,
        frequency_penalty=1.1,
      )
      return [{"generated_text": response.choices[0].message.content.strip()}]
    except Exception as e:
      print(f"Lỗi khi gọi EXTRACT_LLM qua OpenRouter: {e}")
      return []

  print("OpenRouter client và LLM functions (READER_LLM, EXTRACT_LLM) đã sẵn sàng.")
except Exception as e:
  print(f"Lỗi nghiêm trọng khi khởi tạo OpenRouter client: {e}")
  READER_LLM = None
  EXTRACT_LLM = None
  exit()

# --- Prompt Templates ---
prompt_in_chat_format = [
  {
    "role": "system",
    "content": """Bạn là trợ lý hỗ trợ giao tiếp hẹn hò, nhiệm vụ là trả lời câu hỏi dựa trên context chứa nhiều cặp Q/A liên quan.

        QUY TRÌNH BẮT BUỘC:
        1. Context chứa các cặp Q/A (định dạng: Q: ... | A: ...).
        2. Đọc và tổng hợp thông tin từ TẤT CẢ các cặp Q/A trong context để tạo câu trả lời phù hợp nhất với câu hỏi.
        3. Nếu có cặp Q/A khớp gần với câu hỏi (theo ngữ nghĩa), ưu tiên sử dụng ý chính từ câu trả lời đó, nhưng kết hợp với các cặp khác nếu phù hợp.
        4. Nếu context chỉ có một cặp Q/A, sử dụng câu trả lời đó nhưng diễn đạt tự nhiên hơn.
        5. Nếu không có cặp Q/A phù hợp hoặc context trống, trả về: "Mình chưa có đủ thông tin để trả lời chính xác, bạn thử hỏi thêm nhé!"
        6. Câu trả lời phải tự nhiên, ngắn gọn, đúng ngữ cảnh hẹn hò, thân thiện, không lặp lại câu hỏi, và không chứa ký tự thừa.
        7. KHÔNG dịch câu hỏi hoặc trả lời sang tiếng Anh, giữ nguyên tiếng Việt.

        VÍ DỤ:
        Context:
        Q: Tôi nên nhắn gì nếu họ trả lời chậm? | A: Đừng nhắn dồn dập. Chờ khoảng 1-2 ngày, sau đó nhắn lại nhẹ nhàng: "Hey bạn, cuối tuần có gì vui không?". Nếu họ vẫn không trả lời, có thể họ không hứng thú.
        Q: Làm sao để nhắn lại sau vài ngày mà không kỳ? | A: Nhắn tự nhiên, không tỏ vẻ hờn dỗi. "Hey bạn, cuối tuần vui không?" hoặc "Sực nhớ bữa mình đang nói về [chủ đề]...".
        Q: Nếu họ trả lời ngắn, tôi nên làm gì? | A: Có thể họ đang bận hoặc không biết nói gì. Thử đặt một câu hỏi mở hơn, hoặc chia sẻ gì đó về bạn trước để khơi gợi.

        Câu hỏi: Nếu đối phương trả lời tin nhắn chậm thì sao?
        Trả lời: Nếu đối phương trả lời chậm, hãy kiên nhẫn chờ 1-2 ngày, rồi nhắn lại nhẹ nhàng như: "Hey bạn, cuối tuần có gì vui không?". Nếu họ trả lời ngắn hoặc không trả lời, thử đặt câu hỏi mở hơn để khơi gợi, nhưng nếu tình hình không cải thiện, có thể họ không thực sự quan tâm.
        """
  },
  {"role": "user", "content": "Context:\n{context}"},
  {"role": "user", "content": "Câu hỏi: {question}"}
]

# Định dạng thủ công cho RAG_PROMPT_TEMPLATE
RAG_PROMPT_TEMPLATE = """{system_prompt}

Context:
{context}

Câu hỏi: {question}

Trả lời: """
system_prompt = prompt_in_chat_format[0]["content"]
print("RAG_PROMPT_TEMPLATE đã được tạo thủ công.")

AGE_AND_LOCATION_EXTRACTION_PROMPT = [
  {
    "role": "system",
    "content": """Bạn là một trợ lý thông minh, nhiệm vụ là trích xuất độ tuổi tối thiểu (minAge), độ tuổi tối đa (maxAge), và địa điểm (location) từ câu hỏi của người dùng. Trả lời **CHỈ DƯỚI DẠNG JSON** với ba trường: "minAge", "maxAge", và "location". KHÔNG trả về bất kỳ nội dung nào ngoài JSON (không giải thích, không code, không văn bản khác).

        QUY TẮC:
        - Nếu câu hỏi có "trên X tuổi" hoặc "lớn hơn X tuổi", đặt "minAge": X (số nguyên), "maxAge": null.
        - Nếu câu hỏi có "dưới X tuổi" hoặc "nhỏ hơn X tuổi", đặt "minAge": null, "maxAge": X (số nguyên).
        - Nếu câu hỏi có "từ X đến Y tuổi" hoặc "trong khoảng X đến Y tuổi", đặt "minAge": X (số nguyên), "maxAge": Y (số nguyên).
        - Nếu không có thông tin độ tuổi, đặt "minAge": null, "maxAge": null.
        - Chỉ trích xuất **tên địa điểm CỤ THỂ** từ danh sách sau: Hà Nội, TP Hồ Chí Minh, Hải Phòng, Đà Nẵng, Cần Thơ, An Giang, Bà Rịa - Vũng Tàu, Bắc Giang, Bắc Kạn, Bạc Liêu, Bắc Ninh, Bến Tre, Bình Định, Bình Dương, Bình Phước, Bình Thuận, Cà Mau, Cao Bằng, Đắk Lắk, Đắk Nông, Điện Biên, Đồng Nai, Đồng Tháp, Gia Lai, Hà Giang, Hà Nam, Hà Tĩnh, Hải Dương, Hậu Giang, Hòa Bình, Hưng Yên, Khánh Hòa, Kiên Giang, Kon Tum, Lai Châu, Lâm Đồng, Lạng Sơn, Lào Cai, Long An, Nam Định, Nghệ An, Ninh Bình, Ninh Thuận, Phú Thọ, Phú Yên, Quảng Bình, Quảng Nam, Quảng Ngãi, Quảng Ninh, Quảng Trị, Sóc Trăng, Sơn La, Tây Ninh, Thái Bình, Thái Nguyên, Thanh Hóa, Thừa Thiên Huế, Tiền Giang, Trà Vinh, Tuyên Quang, Vĩnh Long, Vĩnh Phúc, Yên Bái.
        - Chuẩn hóa tên địa điểm theo danh sách trên (ví dụ: "TP HCM", "Sài Gòn", "HCM" -> "TP Hồ Chí Minh").
        - Nếu địa điểm không nằm trong danh sách hoặc không được nêu rõ (ví dụ: "gần đây", "ở ngoài"), đặt "location": null.
        - KHÔNG suy diễn hoặc đoán địa điểm. Chỉ trích xuất nếu tên địa điểm được nêu rõ trong câu hỏi.
        - Tuổi phải là số nguyên (int). Sử dụng null cho các trường không có thông tin.

        VÍ DỤ:
        - "Tìm người trên 17 tuổi" -> {"minAge": 17, "maxAge": null, "location": null}
        - "Tìm người dưới 20 tuổi ở Hà Nội" -> {"minAge": null, "maxAge": 20, "location": "Hà Nội"}
        - "Filter Tìm người trong khoảng 10 đến 30 tuổi sống tại TP HCM" -> {"minAge": 10, "maxAge": 30, "location": "TP Hồ Chí Minh"}
        - "Tôi nên nhắn gì đầu tiên?" -> {"minAge": null, "maxAge": null, "location": null}
        - "Gợi ý địa điểm hẹn hò gần đây?" -> {"minAge": null, "maxAge": null, "location": null}
        """
  },
  {"role": "user", "content": "Câu hỏi: {question}"},
]
# --- Từ điển ánh xạ địa điểm ---
LOCATION_MAPPING = {
  # Hà Nội
  "hà nội": "Hà Nội",
  "hn": "Hà Nội",
  "ha noi": "Hà Nội",
  # TP Hồ Chí Minh
  "tp hồ chí minh": "TP Hồ Chí Minh",
  "tp hcm": "TP Hồ Chí Minh",
  "hcm": "TP Hồ Chí Minh",
  "sài gòn": "TP Hồ Chí Minh",
  "sai gon": "TP Hồ Chí Minh",
  "ho chi minh": "TP Hồ Chí Minh",
  # Hải Phòng
  "hải phòng": "Hải Phòng",
  "hp": "Hải Phòng",
  "hai phong": "Hải Phòng",
  # Đà Nẵng
  "đà nẵng": "Đà Nẵng",
  "da nang": "Đà Nẵng",
  "dn": "Đà Nẵng",
  # Cần Thơ
  "cần thơ": "Cần Thơ",
  "can tho": "Cần Thơ",
  # Các tỉnh khác
  "an giang": "An Giang",
  "bà rịa - vũng tàu": "Bà Rịa - Vũng Tàu",
  "bà rịa vũng tàu": "Bà Rịa - Vũng Tàu",
  "ba ria vung tau": "Bà Rịa - Vũng Tàu",
  "bắc giang": "Bắc Giang",
  "bac giang": "Bắc Giang",
  "bắc kạn": "Bắc Kạn",
  "bac kan": "Bắc Kạn",
  "bạc liêu": "Bạc Liêu",
  "bac lieu": "Bạc Liêu",
  "bắc ninh": "Bắc Ninh",
  "bac ninh": "Bắc Ninh",
  "bến tre": "Bến Tre",
  "ben tre": "Bến Tre",
  "bình định": "Bình Định",
  "binh dinh": "Bình Định",
  "bình dương": "Bình Dương",
  "binh duong": "Bình Dương",
  "bình phước": "Bình Phước",
  "binh phuoc": "Bình Phước",
  "bình thuận": "Bình Thuận",
  "binh thuan": "Bình Thuận",
  "cà mau": "Cà Mau",
  "ca mau": "Cà Mau",
  "cao bằng": "Cao Bằng",
  "cao bang": "Cao Bằng",
  "đắk lắk": "Đắk Lắk",
  "dak lak": "Đắk Lắk",
  "đắk nông": "Đắk Nông",
  "dak nong": "Đắk Nông",
  "điện biên": "Điện Biên",
  "dien bien": "Điện Biên",
  "đồng nai": "Đồng Nai",
  "dong nai": "Đồng Nai",
  "đồng tháp": "Đồng Tháp",
  "dong thap": "Đồng Tháp",
  "gia lai": "Gia Lai",
  "hà giang": "Hà Giang",
  "ha giang": "Hà Giang",
  "hà nam": "Hà Nam",
  "ha nam": "Hà Nam",
  "hà tĩnh": "Hà Tĩnh",
  "ha tinh": "Hà Tĩnh",
  "hải dương": "Hải Dương",
  "hai duong": "Hải Dương",
  "hậu giang": "Hậu Giang",
  "hau giang": "Hậu Giang",
  "hòa bình": "Hòa Bình",
  "hoa binh": "Hòa Bình",
  "hưng yên": "Hưng Yên",
  "hung yen": "Hưng Yên",
  "khánh hòa": "Khánh Hòa",
  "khanh hoa": "Khánh Hòa",
  "kiên giang": "Kiên Giang",
  "kien giang": "Kiên Giang",
  "kon tum": "Kon Tum",
  "lai châu": "Lai Châu",
  "lai chau": "Lai Châu",
  "lâm đồng": "Lâm Đồng",
  "lam dong": "Lâm Đồng",
  "lạng sơn": "Lạng Sơn",
  "lang son": "Lạng Sơn",
  "lào cai": "Lào Cai",
  "lao cai": "Lào Cai",
  "long an": "Long An",
  "nam định": "Nam Định",
  "nam dinh": "Nam Định",
  "nghệ an": "Nghệ An",
  "nghe an": "Nghệ An",
  "ninh bình": "Ninh Bình",
  "ninh binh": "Ninh Bình",
  "ninh thuận": "Ninh Thuận",
  "ninh thuan": "Ninh Thuận",
  "phú thọ": "Phú Thọ",
  "phu tho": "Phú Thọ",
  "phú yên": "Phú Yên",
  "phu yen": "Phú Yên",
  "quảng bình": "Quảng Bình",
  "quang binh": "Quảng Bình",
  "quảng nam": "Quảng Nam",
  "quang nam": "Quảng Nam",
  "quảng ngãi": "Quảng Ngãi",
  "quang ngai": "Quảng Ngãi",
  "quảng ninh": "Quảng Ninh",
  "quang ninh": "Quảng Ninh",
  "quảng trị": "Quảng Trị",
  "quang tri": "Quảng Trị",
  "sóc trăng": "Sóc Trăng",
  "soc trang": "Sóc Trăng",
  "sơn la": "Sơn La",
  "son la": "Sơn La",
  "tây ninh": "Tây Ninh",
  "tay ninh": "Tây Ninh",
  "thái bình": "Thái Bình",
  "thai binh": "Thái Bình",
  "thái nguyên": "Thái Nguyên",
  "thai nguyen": "Thái Nguyên",
  "thanh hóa": "Thanh Hóa",
  "thanh hoa": "Thanh Hóa",
  "thừa thiên huế": "Thừa Thiên Huế",
  "thua thien hue": "Thừa Thiên Huế",
  "tiền giang": "Tiền Giang",
  "tien giang": "Tiền Giang",
  "trà vinh": "Trà Vinh",
  "tra vinh": "Trà Vinh",
  "tuyên quang": "Tuyên Quang",
  "tuyen quang": "Tuyên Quang",
  "vĩnh long": "Vĩnh Long",
  "vinh long": "Vĩnh Long",
  "vĩnh phúc": "Vĩnh Phúc",
  "vinh phuc": "Vĩnh Phúc",
  "yên bái": "Yên Bái",
  "yen bai": "Yên Bái",
}

# --- Hàm chuẩn hóa địa điểm ---
def normalize_location(location: str) -> Optional[str]:
  if not location or not isinstance(location, str):
    return None
  # Chuyển thành chữ thường và bỏ dấu cách thừa
  normalized = location.lower().strip()
  # Ánh xạ địa điểm
  return LOCATION_MAPPING.get(normalized, None)
# --- Hàm trích xuất tuổi và địa điểm ---
def extract_age_from_question(question: str):
  """Trích xuất tuổi và địa điểm từ câu hỏi sử dụng EXTRACT_LLM."""
  if EXTRACT_LLM is None:
    print("Lỗi: EXTRACT_LLM chưa được khởi tạo.")
    return None, None, None

  print(f"Debug: Bắt đầu trích xuất độ tuổi và địa điểm từ câu hỏi: {question}")
  prompt_with_question = [
    {"role": "system", "content": AGE_AND_LOCATION_EXTRACTION_PROMPT[0]["content"]},
    {"role": "user", "content": f"Câu hỏi: {question}"},
  ]
  try:
    final_prompt = (
      f"{AGE_AND_LOCATION_EXTRACTION_PROMPT[0]['content']}\n\n"
      f"Câu hỏi: {question}\n\nTrả lời:"
    )
    response = EXTRACT_LLM(final_prompt)

    if response and isinstance(response, list) and "generated_text" in response[0]:
      result_text = response[0]["generated_text"]
      print(f"Debug: Kết quả JSON thô từ LLM - {result_text}")
      try:
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
          json_str = result_text[json_start:json_end]
          age_location_data = json.loads(json_str)
          min_age = age_location_data.get("minAge")
          max_age = age_location_data.get("maxAge")
          location = age_location_data.get("location")
          min_age = int(min_age) if min_age is not None else None
          max_age = int(max_age) if max_age is not None else None

          # Chuẩn hóa địa điểm
          if location:
            normalized_location = normalize_location(location)
            if normalized_location:
              print(f"Debug: Chuẩn hóa địa điểm '{location}' thành '{normalized_location}'")
              location = normalized_location
            else:
              print(f"Debug: Địa điểm '{location}' không khớp với danh sách, trả về null")
              location = None
          else:
            print(f"Debug: Không có địa điểm trong kết quả, trả về null")
            location = None

          print(f"Debug: Trích xuất thành công - minAge={min_age}, maxAge={max_age}, location={location}")
          return min_age, max_age, location
        else:
          print("Debug: Không tìm thấy JSON hợp lệ trong kết quả LLM.")
          return None, None, None
      except json.JSONDecodeError as e:
        print(f"Debug: Lỗi parse JSON từ kết quả LLM: {e} - Result text: {result_text}")
        return None, None, None
      except ValueError as e:
        print(f"Debug: Lỗi chuyển đổi tuổi sang int: {e}")
        return None, None, None
    else:
      print("Debug: LLM không trả về kết quả hợp lệ.")
      return None, None, None
  except Exception as e:
    print(f"Lỗi trong quá trình trích xuất tuổi/địa điểm: {e}")
    return None, None, None

# --- Hàm phân loại câu hỏi ---
def classify_question_category(question: str) -> Optional[str]:
  question = question.lower()
  meeting_safety_keywords = [
    "an toàn khi gặp", "gặp mặt lần đầu", "chú ý khi gặp", "chỗ nào gặp", "gặp ở đâu", "an toàn lần đầu", "gặp mặt an toàn"
  ]
  advice_caution_keywords = ["chú ý", "an toàn", "nên làm gì", "làm sao", "cẩn thận", "tránh", "lưu ý", "đề phòng"]
  general_safety_keywords = [
    "bảo mật", "tin tưởng", "số điện thoại", "lừa đảo", "giả mạo", "báo cáo", "chặn", "block", "riêng tư", "cẩn trọng", " inf cá nhân"
  ]
  start_conversation_keywords = [
    "đầu tiên", "mới ghép đôi", "nhắn gì", "mở lời", "bắt đầu", "bắt chuyện", "làm quen", "chào hỏi"
  ]
  communication_dating_keywords = [
    "trò chuyện", "hẹn hò", "gặp mặt", "rủ đi", "thú vị", "nhắn tin", "nói chuyện", "duy trì", "hấp dẫn",
    "phản hồi chậm", "chậm", "nhắn tin chậm", "rep chậm", "đọc nhưng không trả lời", "seen nhưng không rep",
    "chờ tin nhắn", "mất hứng thú", "bị lơ", "bị ngó lơ"
  ]
  end_continue_keywords = [
    "tiếp tục", "kết thúc", "chia tay", "thích nhau", "tiến triển", "nghiêm túc", "không hợp", "dừng lại"
  ]
  extract_more_keywords = [
    "kể nhiều", "kể thêm", "mở lòng", "chia sẻ thêm", "kể chuyện", "kể về", "tâm sự", "nói thêm"
  ]

  contains_meeting_word = "gặp mặt" in question or " gặp " in question or question.startswith("gặp ") or question.endswith(" gặp")
  contains_advice_word = any(keyword in question for keyword in advice_caution_keywords)
  if any(keyword in question for keyword in meeting_safety_keywords):
    print("Debug: Classified by specific meeting safety keywords")
    return "Bảo mật & An toàn khi hẹn hò"
  if contains_meeting_word and contains_advice_word:
    print("Debug: Classified by meeting keyword + advice keyword")
    return "Bảo mật & An toàn khi hẹn hò"
  if any(keyword in question for keyword in general_safety_keywords):
    print("Debug: Classified by general safety keywords")
    return "Bảo mật & An toàn khi hẹn hò"
  if any(keyword in question for keyword in start_conversation_keywords):
    print("Debug: Classified by start conversation keywords")
    return "Bắt đầu cuộc trò chuyện"
  if any(keyword in question for keyword in communication_dating_keywords):
    print("Debug: Classified by communication/dating keywords")
    return "Giao tiếp & Hẹn hò"
  if any(keyword in question for keyword in end_continue_keywords):
    print("Debug: Classified by end/continue relationship keywords")
    return "Kết thúc hoặc tiếp tục mối quan hệ"
  if any(keyword in question for keyword in extract_more_keywords):
    print("Debug: Classified by extract more / open up keywords")
    return "Bắt đầu cuộc trò chuyện"
  print("Debug: No specific category matched, returning None")
  return None

# --- Caching và Truy vấn FAISS ---
@lru_cache(maxsize=1000)
def _similarity_search_internal(query_lower_strip: str, k_internal: int) -> List[LangchainDocument]:
  """Hàm sync nội bộ để cache kết quả similarity search."""
  if KNOWLEDGE_VECTOR_DATABASE is None:
    print("Lỗi: KNOWLEDGE_VECTOR_DATABASE chưa được khởi tạo.")
    return []
  try:
    return KNOWLEDGE_VECTOR_DATABASE.similarity_search(query=query_lower_strip, k=k_internal)
  except Exception as e:
    print(f"Lỗi trong KNOWLEDGE_VECTOR_DATABASE.similarity_search: {e}")
    return []

async def query_faiss(question: str, k: int = 5) -> List[LangchainDocument]:
  """Truy vấn FAISS bất đồng bộ với cache."""
  query = question.lower().strip()
  loop = asyncio.get_running_loop()
  try:
    result = await loop.run_in_executor(
      None,
      functools.partial(_similarity_search_internal, query, k)
    )
    return result
  except Exception as e:
    print(f"Lỗi khi chạy query_faiss trong executor: {e}")
    return []

# --- Định nghĩa model request/response ---
class QuestionRequest(BaseModel):
  question: str
  userId: Optional[Union[str, int]] = None

class AnswerResponse(BaseModel):
  answer_id: str
  answer: str
  sources: List[str] = []
  is_exact: bool = False
  filter: Optional[Dict] = None

class FeedbackRequest(BaseModel):
  answer_id: str
  is_satisfied: bool
  comment: Optional[str] = None
  question: str
  answer: str

# Hàm lưu phản hồi
def save_feedback(feedback: FeedbackRequest):
  feedback_data = {
    "answer_id": feedback.answer_id,
    "is_satisfied": feedback.is_satisfied,
    "comment": feedback.comment,
    "question": feedback.question,
    "answer": feedback.answer,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
  }
  feedback_file = "feedback.json"
  if os.path.exists(feedback_file):
    with open(feedback_file, "r", encoding="utf-8") as f:
      try:
        feedbacks = json.load(f)
      except json.JSONDecodeError:
        feedbacks = []
  else:
    feedbacks = []
  feedbacks.append(feedback_data)
  with open(feedback_file, "w", encoding="utf-8") as f:
    json.dump(feedbacks, f, ensure_ascii=False, indent=2)
  print(f"Debug: Saved feedback for answer_id={feedback.answer_id}")

# --- Decorator đo thời gian ---
def measure_time(func):
  @functools.wraps(func)
  async def async_wrapper(*args, **kwargs):
    start_time = time.time()
    result = await func(*args, **kwargs)
    print(f"--- {func.__name__} took {time.time() - start_time:.2f} seconds ---")
    return result

  @functools.wraps(func)
  def sync_wrapper(*args, **kwargs):
    start_time = time.time()
    result = func(*args, **kwargs)
    print(f"--- {func.__name__} took {time.time() - start_time:.2f} seconds ---")
    return result

  return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

# --- Hàm gọi LLM ---
@measure_time
def call_llm(prompt: str) -> List[Dict[str, str]]:
  """Gọi READER_LLM và xử lý lỗi."""
  if not isinstance(prompt, str):
    print(f"Lỗi: prompt phải là string, nhận được {type(prompt)}")
    return []
  return READER_LLM(prompt)

# --- Hàm chọn top 5 cặp Q/A từ FAISS ---
def select_best_qa(question: str, retrieved_docs: List[LangchainDocument], top_n: int = 5) -> str:
  if not retrieved_docs:
    print("Debug: Không có tài liệu nào được truy xuất từ FAISS")
    return ""
  context = ""
  for i, doc in enumerate(retrieved_docs[:top_n]):
    if doc.page_content and doc.metadata.get("answer"):
      print(f"Debug: Tài liệu {i+1} - Q: {doc.page_content} | A: {doc.metadata['answer']} | Category: {doc.metadata['category']}")
      context += f"Q: {doc.page_content} | A: {doc.metadata['answer']}\n\n"
  return context.strip()

# --- API endpoint chính ---
@measure_time
@app.post("/answer", response_model=AnswerResponse)
async def answer(request: QuestionRequest):
  print(f"\n--- New Request ---")
  print(f"Debug: Raw request - {request}")
  question = request.question
  if not question or not question.strip():
    print("Warning: Received empty or whitespace-only question.")
    return AnswerResponse(answer="Câu hỏi không được để trống.")
  print(f"Received question: {question}")
  user_id = request.userId
  print(f"Received question from user_id={user_id}")
  answer_id = str(uuid.uuid4())
  print(f"Received question: {question}, answer_id={answer_id}")

  # --- Phần trích xuất tuổi/địa điểm và gọi API user ---
  if question.lower().startswith("filter"):
    start_extract_time = time.time()
    min_age, max_age, location = extract_age_from_question(question)
    print(f"Debug: Age/Location extraction took {time.time() - start_extract_time:.2f} seconds")

    if min_age is not None or max_age is not None or location is not None:
      print(f"Extracted age range: {min_age} - {max_age}, location={location}")
      data = {
        "action": "find_matches",
        "id": user_id,
        "minAge": min_age,
        "maxAge": max_age,
        "location": location
      }

      try:
        response = requests.post(
          "http://localhost:8080/cupid-again/php/match_api.php",
          json=data,
          headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
          user_list = response.json()
          if user_list:
            answer = f"Có {len(user_list)} người "
            if min_age is not None and max_age is not None:
              answer += f"trong độ tuổi từ {min_age} đến {max_age}"
            elif min_age is not None:
              answer += f"trên {min_age} tuổi"
            elif max_age is not None:
              answer += f"dưới {max_age} tuổi"
            if location is not None:
              answer += f" và sống ở {location}"
            answer += ". Đang tải danh sách..."
            return AnswerResponse(
              answer_id=answer_id,
              answer=answer,
              filter={"minAge": min_age, "maxAge": max_age, "location": location},
              is_exact=True
            )
          else:
            return AnswerResponse(
              answer_id=answer_id,
              answer="Không tìm thấy người dùng phù hợp với độ tuổi này.")
        else:
          return AnswerResponse(answer="Không thể lấy dữ liệu người dùng từ hệ thống.")
      except requests.RequestException as e:
        print(f"Error calling match_api.php: {e}")
        return AnswerResponse(
          answer_id=answer_id,
          answer="Lỗi khi gọi hệ thống tìm kiếm.")

  # --- Phần xử lý câu hỏi thông thường (RAG) ---
  quick_responses = {
    "chào": "Chào bạn! Hôm nay bạn thấy thế nào? 😊",
    "cảm ơn": "Không có gì, mình luôn sẵn sàng giúp bạn! 😊",
    "hi": "Hi! Rất vui được trò chuyện với bạn! 😄",
    "hello": "Hello! Bạn khỏe không? 😊",
    "tạm biệt": "Tạm biệt! Hẹn gặp lại bạn nhé. 👋",
    "trời hôm nay đẹp nhỉ": "Ừ, trời đẹp thật! Bạn định làm gì hôm nay? 😊"
  }
  question_lower = question.lower()
  if question_lower in quick_responses:
    print("Debug: Matched quick response.")
    time.sleep(1.5)
    return AnswerResponse(
      answer_id=answer_id,
      answer=quick_responses[question_lower]
    )

  # Phân loại category
  predicted_category = classify_question_category(question)
  print(f"Debug: Predicted category - {predicted_category}")

  if predicted_category is None:
    print("Debug: No category matched, returning default response.")
    time.sleep(2.0)
    return AnswerResponse(
      answer_id=answer_id,
      answer="Mình chưa có đủ thông tin để trả lời chính xác, bạn thử hỏi thêm nhé!")

  # --- Step 1: Initial Retrieval from FAISS ---
  k_initial_retrieval = 15
  print(f"Debug: Retrieving top {k_initial_retrieval} candidates from FAISS...")
  start_faiss_time = time.time()
  initial_docs = await query_faiss(question, k=k_initial_retrieval)
  print(f"Debug: FAISS retrieval took {time.time() - start_faiss_time:.2f} seconds. Found {len(initial_docs)} initial docs.")

  if not initial_docs:
    return AnswerResponse(
      answer_id=answer_id,
      answer="Không tìm thấy tài liệu nào liên quan trong cơ sở dữ liệu.")

  # --- Step 2: Filter by Category ---
  candidate_docs = initial_docs
  if predicted_category:
    filtered_candidate_docs = [
      doc for doc in initial_docs
      if doc.metadata.get("category") == predicted_category and doc.page_content and doc.metadata.get("answer")
    ]
    if filtered_candidate_docs:
      candidate_docs = filtered_candidate_docs
      print(f"Debug: Filtered to {len(candidate_docs)} valid docs in category '{predicted_category}'.")
    else:
      print(f"Debug: No valid docs found in category '{predicted_category}'. Checking initial docs...")
      candidate_docs = [doc for doc in initial_docs if doc.page_content and doc.metadata.get("answer")]
      if candidate_docs:
        print(f"Debug: Using {len(candidate_docs)} valid initial docs for re-ranking.")
  else:
    candidate_docs = [doc for doc in initial_docs if doc.page_content and doc.metadata.get("answer")]
    if candidate_docs:
      print(f"Debug: No category predicted. Using {len(candidate_docs)} valid initial docs for re-ranking.")

  if not candidate_docs:
    print("Debug: No valid candidate documents found after filtering.")
    return AnswerResponse(
      answer_id=answer_id,
      answer="Không tìm thấy tài liệu phù hợp để xử lý.")

  # --- Step 3: Prepare Context from Top 5 Documents ---
  context = select_best_qa(question, candidate_docs, top_n=5)
  print(f"Debug: Context for LLM - {context}")

  # --- Step 4: Call LLM with the refined context ---
  if READER_LLM is None:
    print("Lỗi: READER_LLM chưa sẵn sàng. Trả về câu trả lời mặc định.")
    return AnswerResponse(
      answer_id=answer_id,
      answer="Mình chưa có đủ thông tin để trả lời chính xác, bạn thử hỏi thêm nhé!"
    )

  final_prompt = RAG_PROMPT_TEMPLATE.format(
    system_prompt=system_prompt,
    context=context,
    question=question
  )
  response = call_llm(final_prompt)

  # --- Step 5: Process LLM Response ---
  if response and isinstance(response, list) and "generated_text" in response[0]:
    llm_generated_text = response[0]["generated_text"].strip()
    print(f"Debug: Raw text generated by LLM - '{llm_generated_text}'")

    if not llm_generated_text or llm_generated_text.lower() == "mình chưa có đủ thông tin để trả lời chính xác, bạn thử hỏi thêm nhé!":
      print("Debug: LLM returned empty or default response. Returning default answer.")
      return AnswerResponse(
        answer_id=answer_id,
        answer="Mình chưa có đủ thông tin để trả lời chính xác, bạn thử hỏi thêm nhé!",
        sources=["FAISS Retrieval"]
      )

    return AnswerResponse(
      answer_id=answer_id,
      answer=llm_generated_text,
      sources=["FAISS Retrieval"]
    )
  else:
    print("Debug: LLM did not return a valid response. Falling back to default answer.")
    return AnswerResponse(
      answer_id=answer_id,
      answer="Mình chưa có đủ thông tin để trả lời chính xác, bạn thử hỏi thêm nhé!",
      sources=["FAISS Retrieval"]
    )

# API endpoint cho phản hồi
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
  print(f"\n------ New Feedback ------")
  print(f"Debug: Feedback received - answer_id={feedback.answer_id}, is_satisfied={feedback.is_satisfied}")
  save_feedback(feedback)
  return {"message": "Phản hồi đã được ghi nhận. Cảm ơn bạn!"}

# --- Chạy ứng dụng ---
if __name__ == "__main__":
  print("--- Application Startup ---")
  components_ok = True
  if KNOWLEDGE_VECTOR_DATABASE is None:
    print("FATAL: FAISS index not loaded.")
    components_ok = False
  if READER_LLM is None or EXTRACT_LLM is None:
    print("FATAL: LLM Functions not loaded.")
    components_ok = False

  if components_ok:
    print("Core components (FAISS, LLM Functions) loaded successfully.")
    print(f"Starting Uvicorn server on http://127.0.0.1:8081")
    uvicorn.run(app, host="127.0.0.1", port=8081)
  else:
    print("Application startup failed due to missing components.")

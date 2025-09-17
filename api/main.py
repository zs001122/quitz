from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from services.storage import storage
from services.retriever import retrieve_relevant_context
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-xxxxxx"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    try:
        storage.save_file(file)
        return storage.summary()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/index")
async def index_files():
    try:
        storage.index_files()
        return storage.summary(success=True, message="Files indexed successfully")
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/chat")
async def chat(data: dict):
    question = data.get("message", "")
    if not storage.has_files():
        return {"reply": "No files uploaded yet. Please upload a document first."}

    context = retrieve_relevant_context(question, storage.file_paragraphs)

    system_instruction = (
        f"用户问题: {question}\n\n"
        f"检索到的相关内容:\n{context}\n\n"
        f"原文:{storage.file_paragraphs} 请基于上述内容回答问题，使用markdown格式输出。"
    )

    try:
        completion = client.chat.completions.create(
            model="deepseek-v3.1",
            messages=[{"role": "user", "content": system_instruction}]
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"调用模型出错: {str(e)}"}

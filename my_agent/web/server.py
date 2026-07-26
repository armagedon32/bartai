import json
import asyncio
import io
from pathlib import Path
from typing import AsyncGenerator

import base64
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from my_agent.config import Config
from my_agent.agent import Agent
from my_agent.conversations import ConversationManager
from my_agent import auth

config = Config()
agent = Agent(config)

HERE = Path(__file__).parent
UPLOAD_DIR = HERE / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_agents: dict[int, Agent] = {}


def get_agent_for_user(user_id: int) -> Agent:
    if user_id not in _agents:
        conv_dir = auth.get_user_conversation_dir(user_id)
        new_agent = Agent(config)
        new_agent.conversations = ConversationManager(str(conv_dir))
        _agents[user_id] = new_agent
    return _agents[user_id]


async def get_current_user(authorization: str = Header("")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    user = auth.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


class FileItem(BaseModel):
    name: str
    type: str = "text/plain"
    content: str = ""

class ChatRequest(BaseModel):
    message: str
    conversation: str = "default"
    images: list[str] | None = None
    files: list[FileItem] | None = None

class RenameRequest(BaseModel):
    name: str

class ModelRequest(BaseModel):
    model: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class VerifyRequest(BaseModel):
    email: str
    code: str

class LoginRequest(BaseModel):
    email: str
    password: str

app = FastAPI(title="BArt AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# --- Auth Endpoints ---

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    result = auth.send_verification_code(req.email, req.password, req.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": result["message"]}


@app.post("/api/auth/verify")
async def verify(req: VerifyRequest):
    result = auth.verify_email(req.email, req.code)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": result["message"]}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    result = auth.login_user(req.email, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@app.post("/api/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    auth.logout_token(user.get("_token", ""))
    return {"message": "Logged out"}


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": {k: v for k, v in user.items() if k != "_token"}}


# --- Protected API ---

async def event_stream(message: str, user_id: int, images: list[str] | None = None, files: list[dict] | None = None) -> AsyncGenerator[str, None]:
    ua = get_agent_for_user(user_id)
    try:
        async for event in ua.chat_stream_async(message, images=images, files=files):
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
            if event["type"] == "done":
                _auto_rename(ua, message)
                break
            if event["type"] == "error":
                break
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'content': str(e)})}\n\n"


def _auto_rename(ua, message: str):
    name = ua.conversations.current
    if not name.startswith("chat_"):
        return
    title = message.strip()[:40].rstrip(".,;:!? ")
    if not title:
        return
    new_name = "".join(c if c.isalnum() or c in " -" else "_" for c in title).strip()[:50].rstrip("_")
    if new_name:
        ua.conversations.rename(name, new_name)


@app.get("/")
async def index():
    html = (HERE / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/api/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    if req.conversation != ua.conversations.current:
        result = ua.conversations.switch(req.conversation, create=False)
        if result.endswith("not found."):
            ua.conversations.switch("default")
            return StreamingResponse(
                event_stream(req.message, user["id"], images=req.images, files=None),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )
    files_dict = None
    if req.files:
        files_dict = [f.model_dump() for f in req.files]
    return StreamingResponse(
        event_stream(req.message, user["id"], images=req.images, files=files_dict),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    convs = ua.conversations.list_all()
    return {"conversations": convs, "current": ua.conversations.current}


@app.post("/api/conversations")
async def create_conversation(user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    name = f"chat_{uuid.uuid4().hex[:8]}"
    ua.conversations.switch(name)
    return {"conversations": ua.conversations.list_all(), "current": ua.conversations.current}


@app.delete("/api/conversations/{name}")
async def delete_conversation(name: str, user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    result = ua.conversations.delete(name)
    return {"message": result, "conversations": ua.conversations.list_all(), "current": ua.conversations.current}


@app.post("/api/conversations/{name}/rename")
async def rename_conversation(name: str, req: RenameRequest, user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    result = ua.conversations.rename(name, req.name)
    return {"message": result, "conversations": ua.conversations.list_all(), "current": ua.conversations.current}


@app.get("/api/conversations/{name}/messages")
async def get_messages(name: str, user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    return {"messages": ua.conversations.get_history(name)}


@app.post("/api/conversations/{name}/switch")
async def switch_conversation(name: str, user: dict = Depends(get_current_user)):
    ua = get_agent_for_user(user["id"])
    result = ua.conversations.switch(name, create=False)
    if result.endswith("not found."):
        return {"message": result, "current": ua.conversations.current}
    return {"message": result, "current": ua.conversations.current}


@app.post("/api/extract-text")
async def extract_text(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    content_bytes = await file.read()
    filename = file.filename or "file"
    ext = Path(filename).suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        elif ext in (".docx", ".doc"):
            from docx import Document
            doc = Document(io.BytesIO(content_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            text = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text: {e}")
    if not text.strip():
        text = f"[No extractable text found in {filename}]"
    return {"name": filename, "type": f"text/{ext.lstrip('.')}", "content": text[:100000]}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = Path(file.filename).suffix if file.filename else ".png"
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name
    content = await file.read()
    path.write_bytes(content)
    url = f"/uploads/{name}"
    b64 = base64.b64encode(content).decode()
    mime = f"image/{ext.lstrip('.').replace('jpg', 'jpeg')}"
    data_uri = f"data:{mime};base64,{b64}"
    return {"url": url, "data_uri": data_uri, "name": name}


@app.get("/api/config")
async def get_config(user: dict = Depends(get_current_user)):
    return {"model": config.model, "temperature": config.temperature, "max_tokens": config.max_tokens}


@app.post("/api/config/model")
async def set_model(req: ModelRequest, user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can change model")
    config.model = req.model
    agent.llm.model = req.model
    return {"model": config.model}


@app.on_event("startup")
async def startup():
    auth.init_db()
    auth.seed_admin()
    agent.scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    agent.scheduler.stop()


def run(port: int = 8080):
    import uvicorn
    import os
    port = int(os.environ.get("PORT", port))
    print(f"Web UI: http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

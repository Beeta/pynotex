"""
FastAPI server for Notex (对应 Go 的 server.go)
"""
import logging
import os
import uuid
from pathlib import Path
from typing import Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import Config
from app.vector import VectorStore
from app.store import Store
from app.agent import Agent
from app.types import (
    Notebook, Source, Note, ChatSession,
    TransformationRequest, ChatRequest, ChatResponse,
    HealthResponse, ConfigResponse, ErrorResponse, SourceSummary
)


async def create_server(config: Config) -> FastAPI:
    """创建 FastAPI 服务器（对应 Go 的 NewServer）"""

    # 初始化组件
    vector_store = VectorStore(config)
    store = Store(config)
    await store.init_schema()
    agent = Agent(config, vector_store)

    # 恢复向量索引
    notebooks = await store.list_notebooks()
    logging.info(f"🔄 restoring vector index for {len(notebooks)} notebooks...")
    for nb in notebooks:
        sources = await store.list_sources(nb.id)
        for src in sources:
            if src.content:
                await vector_store.ingest_text(src.name, src.content)
    stats = await vector_store.get_stats()
    logging.info(f"✅ vector index restored: {stats.total_documents} documents")

    # 创建 FastAPI 应用
    app = FastAPI(title="Notex", version="1.0.0")

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载静态文件
    frontend_static = Path("frontend/static")
    if frontend_static.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_static)), name="static")

    uploads_dir = Path("./data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    # 首页
    @app.get("/", response_class=HTMLResponse)
    async def index():
        frontend_index = Path("frontend/index.html")
        if frontend_index.exists():
            return frontend_index.read_text(encoding="utf-8")
        return "<h1>Notex</h1><p>Frontend not found. Please copy frontend files to frontend/</p>"

    # Health check
    @app.get("/api/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            status="ok",
            version="1.0.0",
            timestamp=int(datetime.now().timestamp()),
            services={
                "vector_store": config.vector_store_type,
                "llm": config.openai_model
            }
        )

    @app.get("/api/config", response_model=ConfigResponse)
    async def get_config():
        return ConfigResponse(allow_delete=config.allow_delete)

    # Notebook routes

    @app.get("/api/notebooks")
    async def list_notebooks():
        return await store.list_notebooks()

    @app.post("/api/notebooks")
    async def create_notebook(req: Dict):
        name = req.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        description = req.get("description", "")
        metadata = req.get("metadata", {})
        return await store.create_notebook(name, description, metadata)

    @app.get("/api/notebooks/{notebook_id}")
    async def get_notebook(notebook_id: str):
        nb = await store.get_notebook(notebook_id)
        if not nb:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return nb

    @app.put("/api/notebooks/{notebook_id}")
    async def update_notebook(notebook_id: str, req: Dict):
        name = req.get("name", "")
        description = req.get("description", "")
        metadata = req.get("metadata", {})
        nb = await store.update_notebook(notebook_id, name, description, metadata)
        if not nb:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return nb

    @app.delete("/api/notebooks/{notebook_id}", status_code=204)
    async def delete_notebook(notebook_id: str):
        await store.delete_notebook(notebook_id)
        return None

    # Source routes

    @app.get("/api/notebooks/{notebook_id}/sources")
    async def list_sources(notebook_id: str):
        return await store.list_sources(notebook_id)

    @app.post("/api/notebooks/{notebook_id}/sources")
    async def add_source(notebook_id: str, req: Dict):
        name = req.get("name")
        source_type = req.get("type")
        if not name or not source_type:
            raise HTTPException(status_code=400, detail="name and type are required")

        url = req.get("url")
        content = req.get("content")
        metadata = req.get("metadata", {})

        # 如果提供了 URL，从 URL 获取内容
        if url and not content:
            logging.info(f"fetching content from URL: {url}")
            try:
                content = await vector_store.extract_from_url(url)
                logging.info(f"URL content fetched successfully, size: {len(content)} bytes")
            except Exception as e:
                logging.error(f"failed to fetch URL content: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch URL content: {e}")

        source = Source(
            notebook_id=notebook_id,
            name=name,
            type=source_type,
            url=url,
            content=content,
            metadata=metadata
        )

        created_source = await store.create_source(source)

        # 摄取到向量库
        if created_source.content:
            chunk_count = await vector_store.ingest_text(created_source.name, created_source.content)
            await store.update_source_chunk_count(created_source.id, chunk_count)
            created_source.chunk_count = chunk_count

        return created_source

    @app.delete("/api/notebooks/{notebook_id}/sources/{source_id}", status_code=204)
    async def delete_source(notebook_id: str, source_id: str):
        await store.delete_source(source_id)
        return None

    # Upload route

    @app.post("/api/upload")
    async def upload_file(
        file: UploadFile = File(...),
        notebook_id: str = Form(...)
    ):
        # 保存文件
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(file.filename).suffix
        base_name = Path(file.filename).stem
        unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = upload_dir / unique_filename

        # 写入文件
        content_bytes = await file.read()
        file_path.write_bytes(content_bytes)

        # 提取内容
        try:
            text_content = await vector_store.extract_document(str(file_path))
        except Exception as e:
            logging.error(f"failed to extract document content: {e}")
            file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to extract document content: {e}")

        # 创建 source
        source = Source(
            notebook_id=notebook_id,
            name=file.filename,
            type="file",
            file_name=unique_filename,
            file_size=len(content_bytes),
            content=text_content,
            metadata={"path": str(file_path)}
        )

        created_source = await store.create_source(source)

        # 摄取到向量库
        if created_source.content:
            chunk_count = await vector_store.ingest_text(created_source.name, created_source.content)
            await store.update_source_chunk_count(created_source.id, chunk_count)
            created_source.chunk_count = chunk_count

        return created_source

    # Note routes

    @app.get("/api/notebooks/{notebook_id}/notes")
    async def list_notes(notebook_id: str):
        return await store.list_notes(notebook_id)

    @app.post("/api/notebooks/{notebook_id}/notes")
    async def create_note(notebook_id: str, req: Dict):
        title = req.get("title")
        content = req.get("content")
        note_type = req.get("type")
        if not all([title, content, note_type]):
            raise HTTPException(status_code=400, detail="title, content, and type are required")

        source_ids = req.get("source_ids", [])

        note = Note(
            notebook_id=notebook_id,
            title=title,
            content=content,
            type=note_type,
            source_ids=source_ids
        )

        return await store.create_note(note)

    @app.delete("/api/notebooks/{notebook_id}/notes/{note_id}", status_code=204)
    async def delete_note(notebook_id: str, note_id: str):
        await store.delete_note(note_id)
        return None

    # Transform route

    @app.post("/api/notebooks/{notebook_id}/transform")
    async def transform(notebook_id: str, req: TransformationRequest):
        # 获取 sources
        sources = await store.list_sources(notebook_id)

        if req.source_ids:
            source_map = {s.id: s for s in sources}
            sources = [source_map[sid] for sid in req.source_ids if sid in source_map]
        else:
            req.source_ids = [s.id for s in sources]

        if not sources:
            raise HTTPException(status_code=400, detail="No sources available")

        # 生成转换
        try:
            response = await agent.generate_transformation(req, sources)
        except Exception as e:
            logging.error(f"Generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

        metadata = {
            "length": req.length,
            "format": req.format
        }

        # 如果是 infograph，生成图片
        if req.type == "infograph" and agent.gemini:
            try:
                extra = "**注意：无论来源是什么语言，请务必使用中文**"
                prompt = response.content + "\n\n" + extra
                image_path = await agent.gemini.generate_image("gemini-3-pro-image-preview", prompt)
                web_path = "/uploads/" + Path(image_path).name
                metadata["image_url"] = web_path
            except Exception as e:
                logging.error(f"failed to generate infographic image: {e}")
                metadata["image_error"] = str(e)

        # 如果是 ppt，为每张幻灯片生成图片
        if req.type == "ppt" and agent.gemini:
            slides = agent.parse_ppt_slides(response.content)
            if len(slides) > 10:
                logging.error(f"ppt contains too many slides ({len(slides)}), maximum allowed is 20. skipping image generation.")
                metadata["image_error"] = "PPT页数超过20页上限，已停止生成图片"
            else:
                slide_urls = []
                logging.info(f"generating {len(slides)} slides for ppt...")

                for i, slide in enumerate(slides):
                    logging.info(f"generating image for slide {i+1}/{len(slides)}...")
                    try:
                        prompt = f"Style: {slides[0].style}\n\nSlide Content: {slide.content}"
                        prompt += "\n\n**注意：无论来源是什么语言，请务必使用中文**\n"
                        image_path = await agent.gemini.generate_image("gemini-3-pro-image-preview", prompt)
                        slide_urls.append("/uploads/" + Path(image_path).name)
                    except Exception as e:
                        logging.error(f"failed to generate slide {i+1}: {e}")
                        continue

                metadata["slides"] = slide_urls

        # 保存为 note
        note_content = response.content
        if req.type == "infograph":
            note_content = ""  # infograph 只显示图片

        note = Note(
            notebook_id=notebook_id,
            title=_get_title_for_type(req.type),
            content=note_content,
            type=req.type,
            source_ids=req.source_ids,
            metadata=metadata
        )

        created_note = await store.create_note(note)

        # 如果是 insight，将结果作为新 source 存储
        if req.type == "insight":
            insight_source = Source(
                notebook_id=notebook_id,
                name="洞察报告",
                type="insight",
                content=response.content,
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "source_ids": req.source_ids
                }
            )

            try:
                created_insight = await store.create_source(insight_source)
                chunk_count = await vector_store.ingest_text(created_insight.name, created_insight.content)
                await store.update_source_chunk_count(created_insight.id, chunk_count)
            except Exception as e:
                logging.error(f"failed to create insight source: {e}")

        return created_note

    # Chat routes

    @app.get("/api/notebooks/{notebook_id}/chat/sessions")
    async def list_chat_sessions(notebook_id: str):
        return await store.list_chat_sessions(notebook_id)

    @app.post("/api/notebooks/{notebook_id}/chat/sessions")
    async def create_chat_session(notebook_id: str, req: Dict):
        title = req.get("title", "")
        return await store.create_chat_session(notebook_id, title)

    @app.delete("/api/notebooks/{notebook_id}/chat/sessions/{session_id}", status_code=204)
    async def delete_chat_session(notebook_id: str, session_id: str):
        await store.delete_chat_session(session_id)
        return None

    @app.post("/api/notebooks/{notebook_id}/chat/sessions/{session_id}/messages")
    async def send_message(notebook_id: str, session_id: str, req: ChatRequest):
        # 添加用户消息
        await store.add_chat_message(session_id, "user", req.message, [])

        # 获取会话历史
        session = await store.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 生成回复
        try:
            response = await agent.chat(notebook_id, req.message, session.messages)
        except Exception as e:
            logging.error(f"Chat failed: {e}")
            raise HTTPException(status_code=500, detail=f"Chat failed: {e}")

        # 添加助手消息
        source_ids = [src.id for src in response.sources]
        await store.add_chat_message(session_id, "assistant", response.message, source_ids)

        return response

    @app.post("/api/notebooks/{notebook_id}/chat", response_model=ChatResponse)
    async def chat(notebook_id: str, req: ChatRequest):
        # 创建或获取 session
        session_id = req.session_id
        if not session_id:
            session = await store.create_chat_session(notebook_id, "")
            session_id = session.id

        # 获取会话历史
        session = await store.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 生成回复
        try:
            response = await agent.chat(notebook_id, req.message, session.messages)
        except Exception as e:
            logging.error(f"Chat failed: {e}")
            raise HTTPException(status_code=500, detail=f"Chat failed: {e}")

        response.session_id = session_id

        # 保存消息
        source_ids = [src.id for src in response.sources]
        await store.add_chat_message(session_id, "user", req.message, [])
        await store.add_chat_message(session_id, "assistant", response.message, source_ids)

        return response

    return app


def _get_title_for_type(t: str) -> str:
    """获取转换类型的中文标题"""
    titles = {
        "summary": "摘要",
        "faq": "常见问题解答",
        "study_guide": "学习指南",
        "outline": "大纲",
        "podcast": "播客脚本",
        "timeline": "时间线",
        "glossary": "术语表",
        "quiz": "测验",
        "infograph": "信息图",
        "ppt": "幻灯片",
        "mindmap": "思维导图",
        "insight": "洞察报告",
    }
    return titles.get(t, "笔记")

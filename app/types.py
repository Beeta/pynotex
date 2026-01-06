"""
Data models for Notex (对应 Go 的 types.go)
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class Notebook(BaseModel):
    """笔记本"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Source(BaseModel):
    """文档来源"""
    id: Optional[str] = None
    notebook_id: str
    name: str
    type: str  # "file", "url", "text", "youtube"
    url: Optional[str] = None
    content: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    chunk_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Note(BaseModel):
    """生成的笔记"""
    id: Optional[str] = None
    notebook_id: str
    title: str
    content: str
    type: str  # "summary", "faq", "study_guide", etc.
    source_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """聊天消息"""
    id: Optional[str] = None
    session_id: str
    role: str  # "user", "assistant", "system"
    content: str
    sources: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """聊天会话"""
    id: Optional[str] = None
    notebook_id: str
    title: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Podcast(BaseModel):
    """播客"""
    id: Optional[str] = None
    notebook_id: str
    title: str
    script: Optional[str] = None
    audio_url: Optional[str] = None
    duration: int = 0
    voice: str
    status: str  # "pending", "generating", "completed", "error"
    source_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Request/Response models

class TransformationRequest(BaseModel):
    """内容转换请求"""
    type: str
    prompt: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)
    length: str = "medium"
    format: str = "markdown"


class SourceSummary(BaseModel):
    """来源摘要"""
    id: str
    name: str
    type: str


class TransformationResponse(BaseModel):
    """内容转换响应"""
    type: str
    content: str
    sources: List[SourceSummary]
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str
    sources: List[SourceSummary]
    session_id: str
    message_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: int
    services: Dict[str, str]


class ConfigResponse(BaseModel):
    """配置响应"""
    allow_delete: bool


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str


# Document for vector store
class Document(BaseModel):
    """向量存储的文档"""
    page_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorStats(BaseModel):
    """向量存储统计"""
    total_documents: int
    dimension: int = 1536

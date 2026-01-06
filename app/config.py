"""
Configuration management for Notex
"""
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
import os


@dataclass
class Config:
    """Application configuration"""
    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 8080

    # LLM settings
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Vector store settings
    vector_store_type: str = "sqlite"
    sqlite_path: str = "./data/vector.db"

    # Store settings
    store_path: str = "./data/checkpoints.db"

    # Application settings
    max_sources: int = 5
    max_context_length: int = 128000
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Features
    enable_podcast: bool = True
    enable_markitdown: bool = True
    allow_delete: bool = True

    def is_ollama(self) -> bool:
        """判断是否使用 Ollama"""
        return "11434" in self.openai_base_url or not self.openai_api_key


def load_config() -> Config:
    """加载配置（对应 Go 的 LoadConfig）"""
    load_dotenv()
    load_dotenv(".env.local")  # 本地覆盖

    config = Config(
        server_host=os.getenv("SERVER_HOST", "0.0.0.0"),
        server_port=int(os.getenv("SERVER_PORT", "8080")),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        max_context_length=int(os.getenv("MAX_CONTEXT_LENGTH", "128000")),
        max_sources=int(os.getenv("MAX_SOURCES", "5")),
        enable_markitdown=os.getenv("ENABLE_MARKITDOWN", "true").lower() == "true",
        allow_delete=os.getenv("ALLOW_DELETE", "true").lower() == "true",
    )

    # 自动检测 Ollama
    if not config.openai_base_url and ("ollama" in config.openai_model.lower() or "llama" in config.openai_model.lower()):
        config.openai_base_url = config.ollama_base_url

    return config


def validate_config(config: Config):
    """验证配置"""
    has_openai = bool(config.openai_api_key)
    has_ollama = "11434" in config.openai_base_url

    if not has_openai and not has_ollama:
        raise ValueError("Either OPENAI_API_KEY or OLLAMA_BASE_URL must be set")

    # 确保数据目录存在
    Path(config.store_path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

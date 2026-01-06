"""
Notex - A privacy-first, open-source alternative to NotebookLM
Entry point (对应 Go 的 main.go)
"""
import argparse
import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.config import load_config, validate_config
from app.server import create_server
from app.vector import VectorStore
from app.store import Store

VERSION = "1.0.0"


def setup_logging():
    """配置日志（对应 Go 的 rotatelogs）"""
    Path("./logs").mkdir(exist_ok=True)

    handler = TimedRotatingFileHandler(
        "./logs/notex.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    handler.suffix = "%Y%m%d"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
        handlers=[handler, logging.StreamHandler()]
    )


async def init_app(config):
    """初始化应用（用于 uvicorn）"""
    return await create_server(config)


async def ingest_mode(config, file_path: str, notebook_name: str):
    """摄取模式（导入文档）"""
    logging.info(f"📂 ingesting file: {file_path}...")

    vector_store = VectorStore(config)
    store = Store(config)
    await store.init_schema()

    # 创建或获取 notebook
    notebooks = await store.list_notebooks()
    notebook_id = None
    for nb in notebooks:
        if nb.name == notebook_name:
            notebook_id = nb.id
            break

    if not notebook_id:
        notebook = await store.create_notebook(notebook_name, "Created by ingest mode", {})
        notebook_id = notebook.id
        logging.info(f"📓 created notebook: {notebook_name}")

    # 提取内容
    try:
        content = await vector_store.extract_document(file_path)
    except Exception as e:
        logging.error(f"❌ failed to extract document: {e}")
        return

    # 创建 source
    file_stat = Path(file_path).stat()
    from app.types import Source

    source = Source(
        notebook_id=notebook_id,
        name=Path(file_path).name,
        type="file",
        file_name=Path(file_path).name,
        file_size=file_stat.st_size,
        content=content,
        metadata={"path": file_path}
    )

    await store.create_source(source)

    # 摄取到向量库
    chunk_count = await vector_store.ingest_text(source.name, content)
    logging.info(f"✅ ingestion complete! ({chunk_count} chunks)")


async def init_app(config):
    """初始化应用（用于 uvicorn）"""
    return await create_server(config)


def main():
    parser = argparse.ArgumentParser(description="Notex - Privacy-first AI notebook")
    parser.add_argument("-server", action="store_true", help="Start the web server")
    parser.add_argument("-ingest", type=str, help="Path to a file to ingest")
    parser.add_argument("-notebook", type=str, default="Default Notebook", help="Notebook name for ingest")
    parser.add_argument("-version", action="store_true", help="Show version information")

    args = parser.parse_args()

    if args.version:
        print(f"Notex v{VERSION}")
        print("A privacy-first, open-source alternative to NotebookLM")
        return

    setup_logging()

    config = load_config()
    validate_config(config)

    if args.server:
        # 创建 app 并启动服务器
        import uvicorn

        # 先初始化 app
        app = asyncio.run(init_app(config))

        # 然后运行 uvicorn（这会创建新的事件循环）
        uvicorn.run(
            app,
            host=config.server_host,
            port=config.server_port,
            log_level="info"
        )
    elif args.ingest:
        asyncio.run(ingest_mode(config, args.ingest, args.notebook))
    else:
        parser.print_help()


# 全局 app 实例（用于 uvicorn 直接调用）
app = None

if __name__ == "__main__":
    main()

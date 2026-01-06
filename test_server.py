#!/usr/bin/env python3
"""快速测试服务器启动"""
import asyncio
from app.config import load_config, validate_config
from app.server import create_server

async def main():
    print("🚀 初始化 Notex 服务器...")
    
    config = load_config()
    print(f"✅ 配置加载完成")
    print(f"   - OpenAI Model: {config.openai_model}")
    print(f"   - Server: {config.server_host}:{config.server_port}")
    
    try:
        validate_config(config)
        print("✅ 配置验证通过")
    except ValueError as e:
        print(f"❌ 配置验证失败: {e}")
        return
    
    app = await create_server(config)
    print("✅ 服务器创建成功")
    print(f"   访问: http://{config.server_host}:{config.server_port}")
    print("\n按 Ctrl+C 停止服务器")
    
    import uvicorn
    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")

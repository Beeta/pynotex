# PyNotex

<div align="center">

**A privacy-first, open-source alternative to NotebookLM**

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[English](#english) | [中文](#中文)

</div>

---

## 中文

### 📖 简介

PyNotex 是一个隐私优先的 AI 知识管理系统，完整复刻自 [Notex](https://github.com/sonokai/notex) 项目，使用 Python + FastAPI 实现。

让 AI 帮你从文档中提取洞察、生成摘要、创建学习指南，同时数据完全掌控在你手中。

### ✨ 核心特性

- 🔒 **隐私优先** - 所有数据本地存储，完全掌控
- 🤖 **12 种 AI 转换** - 摘要、FAQ、学习指南、思维导图、PPT 等
- 💬 **RAG 智能对话** - 基于你的文档内容智能问答
- 📁 **多格式支持** - PDF、Word、PPT、Excel、Markdown、TXT
- 🌐 **多模型支持** - OpenAI、Ollama、国产模型（DeepSeek、月之暗面等）
- 🎨 **原生 Web 界面** - 简洁优雅的用户界面
- ⚡ **异步高性能** - 基于 asyncio + aiosqlite

### 🚀 快速开始

#### 前置要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (推荐) 或 pip

#### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/pynotex.git
cd pynotex

# 安装依赖
uv sync

# 配置环境变量
cp env.example .env
# 编辑 .env 文件，设置你的 OPENAI_API_KEY
```

#### 启动服务

```bash
# 使用 uv 启动
uv run python main.py -server

# 或直接使用 uvicorn
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

访问 http://localhost:8080 开始使用！

### 🎯 12 种内容转换

| 类型 | 说明 | 示例用途 |
|------|------|----------|
| **summary** | 综合摘要 | 快速了解文档核心内容 |
| **faq** | 常见问题解答 | 生成问答对，便于查询 |
| **study_guide** | 学习指南 | 结构化学习材料 |
| **outline** | 结构化大纲 | 梳理文档结构 |
| **podcast** | 播客脚本 | 转换为对话形式 |
| **timeline** | 时间线 | 提取时间相关信息 |
| **glossary** | 术语表 | 整理专业术语 |
| **quiz** | 测验题目 | 生成练习题 |
| **mindmap** | Mermaid 思维导图 | 可视化知识结构 |
| **infograph** | 信息图 | 生成可视化图表（需 Gemini） |
| **ppt** | PPT 幻灯片 | 生成演示文稿（需 Gemini） |
| **insight** | 深度洞察报告 | AI 深度分析 |

### 💡 使用场景

#### 📚 学习助手
- 上传课程资料，生成学习指南和测验题
- 创建思维导图梳理知识结构
- 用 RAG 对话深入理解难点

#### 📊 商业分析
- 上传报告文档，生成深度洞察
- 提取关键数据生成信息图
- 创建 PPT 用于汇报

#### 📝 内容创作
- 整理资料生成播客脚本
- 从文档中提取 FAQ
- 生成术语表和时间线

#### 🔍 知识管理
- 建立个人知识库
- 智能搜索和问答
- 多文档关联分析

### 🛠️ 技术栈

| 模块 | 技术 |
|------|------|
| **Web 框架** | FastAPI |
| **数据库** | SQLite (aiosqlite) |
| **LLM** | OpenAI SDK |
| **图片生成** | Google Gemini |
| **文档处理** | markitdown, pymupdf |
| **项目管理** | uv |

### 📦 项目结构

```
pynotex/
├── app/                    # 主应用代码
│   ├── config.py          # 配置管理
│   ├── types.py           # 数据模型
│   ├── prompt.py          # Prompt 模板
│   ├── store.py           # SQLite 存储
│   ├── vector.py          # 向量存储
│   ├── gemini.py          # Gemini 客户端
│   ├── agent.py           # LLM 代理
│   └── server.py          # FastAPI 服务器
├── frontend/              # Web 界面
│   ├── index.html
│   └── static/
├── data/                  # 运行时数据
│   ├── uploads/          # 上传文件
│   └── checkpoints.db    # SQLite 数据库
├── main.py               # 入口文件
├── pyproject.toml        # 项目配置
└── .env.example          # 环境变量模板
```

### ⚙️ 配置选项

#### 使用 OpenAI

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

#### 使用国产模型

```bash
# DeepSeek 示例
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# 月之暗面 Kimi
OPENAI_API_KEY=sk-your-moonshot-key
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-8k
```

#### 使用本地模型（Ollama）

```bash
# 不设置 OPENAI_API_KEY
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

#### 启用图片生成

```bash
# 用于 infograph 和 ppt
GOOGLE_API_KEY=AIza-your-key-here
```

### 📡 API 端点

完整的 RESTful API：

- **健康检查**: `GET /api/health`
- **笔记本**: `GET|POST|PUT|DELETE /api/notebooks`
- **来源管理**: `POST /api/notebooks/:id/sources`
- **文件上传**: `POST /api/upload`
- **内容转换**: `POST /api/notebooks/:id/transform`
- **智能对话**: `POST /api/notebooks/:id/chat`

详见 [API 文档](docs/API.md)

### 🎨 与 Go 版本对比

| 特性 | Go 版本 | PyNotex | 说明 |
|------|---------|---------|------|
| Web 框架 | Gin | FastAPI | 异步 + 自动文档 |
| 数据库 | modernc.org/sqlite | aiosqlite | 完全异步 |
| LLM SDK | langchaingo | openai | 官方 SDK |
| 文档转换 | markitdown CLI | markitdown 库 | 无需外部调用 |
| 性能 | ⚡⚡⚡ | ⚡⚡ | Python 略慢但足够快 |
| 开发效率 | ⭐⭐ | ⭐⭐⭐ | Python 更简洁 |
| 生态丰富度 | ⭐⭐ | ⭐⭐⭐ | Python 生态更丰富 |

### 🔧 开发

```bash
# 安装开发依赖
uv sync --all-extras

# 运行测试
uv run pytest

# 代码格式化
uv run black .

# 类型检查
uv run mypy app/
```

### 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

### 📝 常见问题

**Q: 与 NotebookLM 有什么区别？**  
A: PyNotex 是完全开源和隐私优先的。所有数据都在本地，你可以使用任何 LLM 模型，包括本地模型。

**Q: 需要 GPU 吗？**  
A: 不需要。PyNotex 通过 API 调用 LLM，所有计算在云端或 Ollama 本地服务器完成。

**Q: 支持中文吗？**  
A: 完全支持！所有 Prompt 都针对中文优化，支持中英文文档处理。

**Q: 可以离线使用吗？**  
A: 配合 Ollama 可以完全离线使用（除了图片生成功能）。

**Q: 洞察报告需要 DeepInsight CLI 吗？**  
A: 不需要。如果没有 DeepInsight，会自动使用 LLM 生成深度洞察报告。

### 📄 许可证

[MIT License](LICENSE)

### 🙏 致谢

本项目完整复刻自 [Notex](https://github.com/sonokai/notex)，感谢原作者的开源贡献。

---

## English

### 📖 Introduction

PyNotex is a privacy-first AI knowledge management system, a complete Python reimplementation of the [Notex](https://github.com/sonokai/notex) project using FastAPI.

Let AI help you extract insights, generate summaries, and create study guides from your documents, while keeping full control of your data.

### ✨ Key Features

- 🔒 **Privacy-First** - All data stored locally, fully under your control
- 🤖 **12 AI Transformations** - Summaries, FAQs, study guides, mind maps, PPTs, and more
- 💬 **RAG-powered Chat** - Intelligent Q&A based on your document content
- 📁 **Multi-format Support** - PDF, Word, PPT, Excel, Markdown, TXT
- 🌐 **Multi-model Support** - OpenAI, Ollama, Chinese models (DeepSeek, Moonshot, etc.)
- 🎨 **Native Web UI** - Clean and elegant user interface
- ⚡ **High Performance** - Built on asyncio + aiosqlite

### 🚀 Quick Start

#### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

#### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pynotex.git
cd pynotex

# Install dependencies
uv sync

# Configure environment variables
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

#### Start Server

```bash
# Start with uv
uv run python main.py -server

# Or use uvicorn directly
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

Visit http://localhost:8080 to get started!

### 🎯 12 Content Transformations

| Type | Description | Use Case |
|------|-------------|----------|
| **summary** | Comprehensive summary | Quick overview of document |
| **faq** | Frequently asked questions | Generate Q&A pairs |
| **study_guide** | Study guide | Structured learning materials |
| **outline** | Structured outline | Organize document structure |
| **podcast** | Podcast script | Convert to dialogue format |
| **timeline** | Timeline | Extract time-related info |
| **glossary** | Glossary | List professional terms |
| **quiz** | Quiz questions | Generate practice questions |
| **mindmap** | Mermaid mind map | Visualize knowledge structure |
| **infograph** | Infographic | Generate visual charts (requires Gemini) |
| **ppt** | PowerPoint | Create presentation (requires Gemini) |
| **insight** | Deep insight report | AI deep analysis |

### ⚙️ Configuration

#### Using OpenAI

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

#### Using Chinese Models

```bash
# DeepSeek example
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

#### Using Local Models (Ollama)

```bash
# Don't set OPENAI_API_KEY
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 📄 License

[MIT License](LICENSE)

### 🙏 Credits

This project is a complete reimplementation of [Notex](https://github.com/sonokai/notex). Thanks to the original author for their open-source contribution.

---

<div align="center">

**Built with ❤️ using Python and FastAPI**

[⬆ Back to Top](#pynotex)

</div>

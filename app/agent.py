"""
AI agent for generating transformations and chat responses (对应 Go 的 agent.go)
"""
import logging
import subprocess
import re
import asyncio
from typing import List, Optional
from openai import AsyncOpenAI
from app.config import Config
from app.vector import VectorStore
from app.gemini import GeminiClient
from app.types import TransformationRequest, TransformationResponse, ChatResponse, SourceSummary, Source, ChatMessage
from app.prompt import get_transformation_prompt, chat_system_prompt
from pathlib import Path


class Slide:
    """PPT 幻灯片"""
    def __init__(self, style: str, content: str):
        self.style = style
        self.content = content


class Agent:
    """AI 代理（用于生成内容转换和聊天响应）"""

    def __init__(self, config: Config, vector_store: VectorStore):
        self.config = config
        self.vector_store = vector_store

        # 初始化 OpenAI 客户端
        openai_kwargs = {
            "api_key": config.openai_api_key,
            "max_retries": 3,
            "timeout": 60.0,
        }
        if config.openai_base_url:
            openai_kwargs["base_url"] = config.openai_base_url

        self.llm = AsyncOpenAI(**openai_kwargs)

        # 初始化 Gemini 客户端
        self.gemini = GeminiClient(config.google_api_key) if config.google_api_key else None

    async def generate_transformation(
        self,
        req: TransformationRequest,
        sources: List[Source]
    ) -> TransformationResponse:
        """生成转换（对应 Go 的 GenerateTransformation）"""

        # 构建 source context
        source_context_parts = []
        for i, src in enumerate(sources, 1):
            source_context_parts.append(f"\n## Source {i}: {src.name}\n")

            content = src.content or ""
            limit = self.config.max_context_length

            if len(content) <= limit:
                source_context_parts.append(content)
            else:
                source_context_parts.append(content[:limit])
                source_context_parts.append(f"\n... [Content truncated, total length: {len(content)}]")

            source_context_parts.append("\n")

        source_context = ''.join(source_context_parts)

        # 获取 prompt 模板
        prompt_template = get_transformation_prompt(req.type)

        # 格式化 prompt
        prompt = prompt_template.format(
            sources=source_context,
            type=req.type,
            length=req.length,
            format=req.format,
            prompt=req.prompt or ""
        )

        # 根据类型选择生成方式
        if req.type == "ppt":
            # 使用 Gemini Flash
            if self.gemini:
                response = await self.gemini.generate_text(prompt, "gemini-2.0-flash-exp")
            else:
                response = await self._generate_text(prompt)

        elif req.type == "insight":
            # 先生成摘要
            summary = await self._generate_text(prompt)

            # 尝试调用 DeepInsight，如果不可用则使用 LLM 生成深度分析
            try:
                response = await self._call_deepinsight(summary)
            except FileNotFoundError:
                logging.warning("DeepInsight CLI not found, using LLM for insight generation")
                # 使用 LLM 生成深度洞察
                insight_prompt = f"""基于以下摘要，生成一份深度洞察报告。

摘要内容：
{summary}

请生成一份包含以下内容的深度洞察报告：
1. 核心发现和关键洞察
2. 数据趋势和模式分析
3. 潜在问题和风险
4. 机会识别和建议
5. 战略性思考和建议

报告应该具有深度和前瞻性，提供独特的视角和见解。使用中文输出。"""
                response = await self._generate_text(insight_prompt)
            except Exception as e:
                logging.error(f"DeepInsight execution failed: {e}, falling back to LLM")
                # 发生其他错误也回退到 LLM
                insight_prompt = f"基于以下内容生成深度洞察报告：\n\n{summary}"
                response = await self._generate_text(insight_prompt)

        else:
            # 直接 LLM 生成
            response = await self._generate_text(prompt)

        # 构建 source summaries
        source_summaries = [
            SourceSummary(id=src.id, name=src.name, type=src.type)
            for src in sources
        ]

        return TransformationResponse(
            type=req.type,
            content=response,
            sources=source_summaries,
            metadata={"length": req.length, "format": req.format}
        )

    async def chat(
        self,
        notebook_id: str,
        message: str,
        history: List[ChatMessage]
    ) -> ChatResponse:
        """聊天（基于 RAG，对应 Go 的 Chat）"""

        # 相似度搜索
        docs = await self.vector_store.similarity_search(message, self.config.max_sources)

        # 构建上下文
        context_parts = []
        if docs:
            context_parts.append("来源中的相关信息：\n\n")
            for i, doc in enumerate(docs, 1):
                context_parts.append(f"[来源 {i}] {doc.page_content}\n")
                if "source" in doc.metadata:
                    context_parts.append(f"来源: {doc.metadata['source']}\n\n")

        context = ''.join(context_parts)

        # 构建历史
        history_parts = []
        for msg in history[-10:]:  # 最近 10 条
            role = "用户" if msg.role == "user" else "助手"
            history_parts.append(f"{role}: {msg.content}\n")

        history_text = ''.join(history_parts)

        # 格式化 chat prompt
        prompt = chat_system_prompt().format(
            history=history_text,
            context=context,
            question=message
        )

        # 生成回复
        response_text = await self._generate_text(prompt)

        # 提取 source summaries
        sources = []
        seen = set()
        for doc in docs:
            source_name = doc.metadata.get("source", "")
            if source_name and source_name not in seen:
                sources.append(SourceSummary(id=source_name, name=source_name, type="file"))
                seen.add(source_name)

        return ChatResponse(
            message=response_text,
            sources=sources,
            session_id=notebook_id,
            metadata={"docs_retrieved": len(docs)}
        )

    async def _generate_text(self, prompt: str) -> str:
        """调用 LLM 生成文本"""
        try:
            response = await self.llm.chat.completions.create(
                model=self.config.openai_model,
                messages=[{"role": "user", "content": prompt}],
                timeout=300
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"LLM generation failed: {e}")
            raise

    async def _call_deepinsight(self, summary: str) -> str:
        """调用 DeepInsight 外部工具（对应 Go 的 callDeepInsight）"""
        # 创建临时文件
        tmp_dir = Path("./data/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = tmp_dir / f"deepinsight_report_{int(asyncio.get_event_loop().time() * 1000)}.md"

        try:
            # 执行 DeepInsight 命令
            proc = await asyncio.create_subprocess_exec(
                "./DeepInsight",
                "-o", str(tmp_file),
                summary,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else ""
                raise RuntimeError(f"DeepInsight command failed: {error_msg}")

            # 读取生成的报告
            report_content = tmp_file.read_text(encoding="utf-8")
            return report_content

        except asyncio.TimeoutError:
            raise RuntimeError("DeepInsight command timeout after 10 minutes")
        except Exception as e:
            logging.error(f"DeepInsight execution failed: {e}")
            raise
        finally:
            # 清理临时文件
            if tmp_file.exists():
                tmp_file.unlink()

    def parse_ppt_slides(self, content: str) -> List[Slide]:
        """解析 PPT 幻灯片（对应 Go 的 ParsePPTSlides）"""
        slides = []

        # 1. 提取风格指令
        style = ""
        style_start = content.find("<STYLE_INSTRUCTIONS>")
        style_end = content.find("</STYLE_INSTRUCTIONS>")
        if style_start != -1 and style_end > style_start:
            style = content[style_start + 20:style_end]

        # 2. 按 Slide 标记分割
        pattern = re.compile(r'^(?:\s*#{1,6}\s*)?(?:Slide|幻灯片|第\d+张幻灯片|##)\s*\d+[:\s]*.*$', re.MULTILINE)
        matches = list(pattern.finditer(content))

        if matches:
            for i, match in enumerate(matches):
                start = match.start()
                end = len(content) if i + 1 >= len(matches) else matches[i + 1].start()

                slide_content = content[start:end]

                # 验证：必须包含至少一个必需字段
                lower = slide_content.lower()
                if any(keyword in lower for keyword in ["叙事目标", "narrative goal", "关键内容"]):
                    slides.append(Slide(style=style, content=slide_content))

        # 3. 如果没找到，尝试按 "// 叙事目标" 分割
        if not slides:
            marker = "// 叙事目标"
            if marker not in content:
                marker = "// NARRATIVE GOAL"

            if marker in content:
                parts = content.split(marker)
                for i in range(1, len(parts)):
                    slides.append(Slide(style=style, content=marker + parts[i]))

        # 最终 fallback
        if not slides:
            slides.append(Slide(style=style, content=content))

        return slides

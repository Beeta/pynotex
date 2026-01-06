"""
Vector store and document processing for Notex (对应 Go 的 vector.go)
"""
import logging
from pathlib import Path
from typing import List, Tuple
from app.config import Config
from app.types import Document, VectorStats

# 导入文档处理库
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    logging.warning("markitdown not available, will use fallback text extraction")


class VectorStore:
    """向量存储（使用简化的关键词匹配，对应 Go 版本的实现）"""

    def __init__(self, config: Config):
        self.config = config
        self.docs: List[Document] = []
        self.markitdown = MarkItDown() if config.enable_markitdown and MARKITDOWN_AVAILABLE else None

    async def extract_document(self, file_path: str) -> str:
        """提取文档内容（对应 Go 的 ExtractDocument）"""
        path = Path(file_path)
        ext = path.suffix.lower()

        # 使用 markitdown 转换
        if self.config.enable_markitdown and self.markitdown and self._needs_markitdown(ext):
            try:
                result = self.markitdown.convert(file_path)
                return result.text_content
            except Exception as e:
                logging.error(f"markitdown conversion failed: {e}")
                # Fallback to direct read

        # 直接读取文本文件
        return path.read_text(encoding="utf-8")

    async def extract_from_url(self, url: str) -> str:
        """从 URL 提取内容（对应 Go 的 ExtractFromURL）"""
        if not self.config.enable_markitdown or not self.markitdown:
            raise ValueError("markitdown is disabled, cannot fetch URL content")

        try:
            result = self.markitdown.convert(url)
            return result.text_content
        except Exception as e:
            raise RuntimeError(f"Failed to fetch URL content: {e}")

    async def ingest_text(self, source_name: str, content: str) -> int:
        """摄取文本内容（对应 Go 的 IngestText）"""
        chunks = self._split_text(content)

        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": source_name,
                    "chunk": i
                }
            )
            self.docs.append(doc)

        logging.info(f"[VectorStore] Ingested {len(chunks)} chunks from '{source_name}'")
        return len(chunks)

    def _split_text(self, text: str) -> List[str]:
        """智能分块（对应 Go 的 splitText）

        根据中英文自动选择分块策略：
        - 中文：按字符分块
        - 英文：按单词分块
        """
        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap

        if chunk_size <= 0:
            chunk_size = 1000
        if chunk_overlap < 0:
            chunk_overlap = 200

        logging.info(f"[VectorStore] Splitting text (len={len(text)}, chunk_size={chunk_size}, overlap={chunk_overlap})")

        chunks = []

        # 检测 CJK 字符（中文、日文、韩文）比例
        runes = list(text)
        cjk_count = sum(1 for c in runes if '\u4e00' <= c <= '\u9fff')
        cjk_ratio = cjk_count / len(runes) if runes else 0

        if cjk_ratio > 0.3:
            # 中文：按字符分块
            logging.info("[VectorStore] Using CJK splitting (by character count)")
            i = 0
            while i < len(runes):
                end = min(i + chunk_size, len(runes))
                chunk = ''.join(runes[i:end])
                chunks.append(chunk)

                if end >= len(runes):
                    break
                i += (chunk_size - chunk_overlap)
        else:
            # 英文：按单词分块
            logging.info("[VectorStore] Using word-based splitting")
            words = text.split()

            i = 0
            while i < len(words):
                end = min(i + chunk_size, len(words))
                chunk = ' '.join(words[i:end])
                chunks.append(chunk)

                if end >= len(words):
                    break
                i += (chunk_size - chunk_overlap)

        logging.info(f"[VectorStore] Created {len(chunks)} chunks")
        return chunks

    async def similarity_search(self, query: str, num_docs: int = 5) -> List[Document]:
        """相似度搜索（使用简化的关键词匹配，对应 Go 的 SimilaritySearch）"""
        if num_docs <= 0:
            num_docs = 5

        logging.info(f"[VectorStore] Searching for '{query}' (total docs: {len(self.docs)})")

        if len(self.docs) == 0:
            logging.info("[VectorStore] No documents available for search")
            return []

        # 关键词匹配算法
        query_lower = query.lower()
        query_runes = list(query_lower)

        scored_docs: List[Tuple[Document, float]] = []

        for doc in self.docs:
            content = doc.page_content.lower()
            score = 0.0

            # 1. 子串匹配
            if query_lower in content:
                score += 10.0

            # 2. 字符匹配率
            match_count = sum(1 for c in query_runes if c in content)
            if match_count > 0:
                char_match_ratio = match_count / len(query_runes)
                score += char_match_ratio * 5.0

            # 3. 单词匹配（用于英文）
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2 and word in content:
                    score += 2.0

            # 4. 中文问题关键词加分
            question_keywords = ["介绍", "什么", "啥", "内容", "文档", "说"]
            for keyword in question_keywords:
                if keyword in query_lower:
                    score += 1.0
                    break

            if score > 0:
                scored_docs.append((doc, score))

        logging.info(f"[VectorStore] Found {len(scored_docs)} matching documents")

        # 按分数排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 如果没有匹配，返回所有文档作为 fallback
        if len(scored_docs) == 0:
            logging.info("[VectorStore] No matches found, returning all documents as fallback")
            return self.docs[:num_docs]

        # 返回前 N 个结果
        result = [doc for doc, _ in scored_docs[:num_docs]]

        if result:
            logging.info(f"[VectorStore] Returning top {len(result)} results (best score: {scored_docs[0][1]:.2f})")

        return result

    async def delete(self, source_name: str):
        """删除来源的所有文档"""
        self.docs = [doc for doc in self.docs if doc.metadata.get("source") != source_name]

    async def get_stats(self) -> VectorStats:
        """获取统计信息"""
        dimension = 768 if self.config.is_ollama() else 1536
        return VectorStats(
            total_documents=len(self.docs),
            dimension=dimension
        )

    def _needs_markitdown(self, ext: str) -> bool:
        """检查文件是否需要 markitdown 转换"""
        markitdown_exts = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
        return ext in markitdown_exts

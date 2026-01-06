"""
Gemini client for image generation (对应 Go 的 gemini.go)
"""
import logging
import time
from pathlib import Path
from typing import Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("google-generativeai not available")


class GeminiClient:
    """Gemini 客户端（用于图片生成和文本生成）"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key and GENAI_AVAILABLE:
            genai.configure(api_key=api_key)

    async def generate_image(self, model: str, prompt: str) -> str:
        """生成图片（对应 Go 的 GenerateImage）"""
        if not self.api_key:
            raise ValueError("google_api_key is not set")

        if not GENAI_AVAILABLE:
            raise RuntimeError("google-generativeai package is not installed")

        # 重试逻辑
        for attempt in range(1, 4):
            try:
                # 使用 Imagen 模型生成图片
                imagen = genai.ImageGenerationModel(model)

                result = imagen.generate_images(
                    prompt=prompt,
                    number_of_images=1
                )

                # 保存图片
                image_data = result.images[0]._pil_image
                file_name = f"infograph_{int(time.time() * 1000)}.png"
                file_path = Path(f"./data/uploads/{file_name}")
                file_path.parent.mkdir(parents=True, exist_ok=True)

                image_data.save(file_path)
                logging.info(f"Image saved to {file_path}")
                return str(file_path)

            except Exception as e:
                logging.error(f"Image generation attempt {attempt} failed: {e}")
                if attempt < 3:
                    time.sleep(2)

        raise RuntimeError("Failed to generate image after 3 attempts")

    async def generate_text(self, prompt: str, model: str) -> str:
        """生成文本（使用 Gemini Flash）"""
        if not self.api_key:
            raise ValueError("google_api_key is not set")

        if not GENAI_AVAILABLE:
            raise RuntimeError("google-generativeai package is not installed")

        try:
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Failed to generate text: {e}")


class LLMProvider:
    """LLM 提供者接口（兼容 Go 版本）"""

    def __init__(self, gemini_client: Optional[GeminiClient], llm):
        self.gemini_client = gemini_client
        self.llm = llm

    async def generate_from_single_prompt(self, prompt: str) -> str:
        """从单个提示生成文本"""
        # 这个方法会在 agent.py 中使用 OpenAI SDK 实现
        pass

    async def generate_text_with_model(self, prompt: str, model: str) -> str:
        """使用指定模型生成文本"""
        if self.gemini_client and "gemini" in model.lower():
            return await self.gemini_client.generate_text(prompt, model)
        else:
            # Fallback to default LLM
            return await self.generate_from_single_prompt(prompt)

    async def generate_image(self, model: str, prompt: str) -> str:
        """生成图片"""
        if not self.gemini_client:
            raise RuntimeError("Gemini client not configured")
        return await self.gemini_client.generate_image(model, prompt)

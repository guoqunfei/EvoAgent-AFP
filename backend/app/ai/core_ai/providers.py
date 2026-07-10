from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json

import httpx

from app.ai.core_ai.base import BaseChatProvider, ChatMessage, ChatResult, ChatStreamChunk
from app.core.config import Settings
from typing import Optional, List, Dict


@dataclass
class MockChatProvider:
    provider_name: str = "mock"
    model_name: str = "mock-chat"

    def generate(
        self,
        messages: List[ChatMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ChatResult:
        last_user = next((item.content for item in reversed(messages) if item.role == "user"), "")
        answer = (
            "当前运行的是本地 Mock Chat Provider。\n\n"
            "这说明你还没有启用真实大模型服务，但系统仍然可以完成：\n"
            "1. 本地知识库入库\n"
            "2. SQLite 持久化\n"
            "3. FAISS 检索\n"
            "4. 基础 RAG 回答\n"
            "5. DeepResearch 工作流编排\n\n"
            f"你刚才的问题是：{last_user}\n\n"
            "如果你希望切换到真实模型，请在 `.env.development` 中启用 `LLM__ENABLED=true`，并配置 OpenAI 兼容接口。"
        )
        return ChatResult(text=answer, model=self.model_name, provider=self.provider_name)


@dataclass
class OpenAICompatibleChatProvider:
    base_url: str
    api_key: str
    model_name: str
    timeout_seconds: int = 120
    provider_name: str = "openai-compatible"

    def generate(
        self,
        messages: List[ChatMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ChatResult:
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for message in messages:
            payload_messages.append({"role": message.role, "content": message.content})

        response = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "temperature": temperature if temperature is not None else 0.2,
                "messages": payload_messages,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ChatResult(
            text=text,
            model=self.model_name,
            provider=self.provider_name,
            usage=usage,
            raw=data,
        )

    def generate_stream(
        self,
        messages: List[ChatMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Iterator[ChatStreamChunk]:
        payload_messages: List[dict] = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for message in messages:
            payload_messages.append({"role": message.role, "content": message.content})

        with httpx.stream(
            "POST",
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "temperature": temperature if temperature is not None else 0.2,
                "messages": payload_messages,
                "stream": True,
            },
            timeout=self.timeout_seconds,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        finish = choices[0].get("finish_reason")
                        if content:
                            yield ChatStreamChunk(content=content)
                        if finish:
                            yield ChatStreamChunk(content="", finish_reason=finish)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


def build_chat_provider(settings: Settings) -> BaseChatProvider:
    if settings.llm.enabled and settings.llm.provider == "openai-compatible":
        if not settings.llm.base_url or not settings.llm.api_key:
            raise ValueError("LLM enabled but base_url/api_key is missing.")
        return OpenAICompatibleChatProvider(
            base_url=settings.llm.base_url,
            api_key=settings.llm.api_key,
            model_name=settings.llm.model,
            timeout_seconds=settings.llm.timeout_seconds,
        )
    return MockChatProvider(model_name=settings.llm.model or "mock-chat")


def build_model_provider(settings: Settings, model_key: Optional[str] = None) -> BaseChatProvider:
    """Build a chat provider for a specific model from the CHAT_MODELS config.
    Falls back to the default model if the requested one has no api_key configured."""
    models_cfg = settings.chat_models
    key = model_key or models_cfg.default

    model_item = models_cfg.models.get(key)
    if model_item and model_item.api_key and model_item.base_url:
        return OpenAICompatibleChatProvider(
            base_url=model_item.base_url,
            api_key=model_item.api_key,
            model_name=model_item.model,
            timeout_seconds=settings.llm.timeout_seconds,
            provider_name=key,
        )

    # Fallback to default
    default_item = models_cfg.models.get(models_cfg.default)
    if default_item and default_item.api_key and default_item.base_url:
        return OpenAICompatibleChatProvider(
            base_url=default_item.base_url,
            api_key=default_item.api_key,
            model_name=default_item.model,
            timeout_seconds=settings.llm.timeout_seconds,
            provider_name=models_cfg.default,
        )

    # Ultimate fallback to legacy LLM config
    return build_chat_provider(settings)


def list_available_models(settings: Settings) -> List[dict]:
    """Return models available for frontend switching.
    A model is 'ready' if it has an api_key configured."""
    models_cfg = settings.chat_models
    result = []
    for key, item in models_cfg.models.items():
        result.append({
            "id": key,
            "label": _model_label(key),
            "model": item.model,
            "ready": bool(item.api_key and item.base_url),
        })
    return result


def _model_label(key: str) -> str:
    labels: Dict[str, str] = {
        "deepseek": "DeepSeek",
        "gpt": "GPT-4o",
        "gemini": "Gemini",
        "claude": "Claude",
    }
    return labels.get(key, key.title())
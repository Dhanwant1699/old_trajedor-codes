"""
Unified Multi-Provider LLM Client for Claude XAUUSD AI Trading Council.
Supports:
- NVIDIA NIM Cloud (deepseek-ai/deepseek-v4-flash-0731, deepseek-ai/deepseek-r1, meta/llama-3.3-70b-instruct)
- Anthropic Claude (claude-sonnet-5, claude-3-7-sonnet)
- Groq Cloud (llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b)
- Local Ollama (deepseek-r1:14b, qwen2.5:14b)
"""

import json
from typing import Dict, Any, Optional, List
import anthropic
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config import CONFIG, get_model_api_kwargs


class UnifiedLLMClient:
    """
    Unified client routing calls across Anthropic Claude, NVIDIA NIM, Groq, and Local Ollama.
    """
    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        self.provider = (provider or CONFIG.AI_PROVIDER).lower()
        self.model = model or (CONFIG.NVIDIA_MODEL if self.provider == "nvidia" else CONFIG.CLAUDE_MODEL)
        self.api_key = api_key or (CONFIG.NVIDIA_API_KEY if self.provider == "nvidia" else CONFIG.ANTHROPIC_API_KEY)

        self.anthropic_client = None
        self.openai_compatible_client = None

        if self.provider == "anthropic" and self.api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.api_key)

        elif self.provider == "nvidia" and OpenAI:
            # NVIDIA NIM endpoint
            base_url = "https://integrate.api.nvidia.com/v1"
            self.openai_compatible_client = OpenAI(base_url=base_url, api_key=self.api_key or "nvapi-placeholder")

        elif self.provider == "groq" and OpenAI:
            base_url = "https://api.groq.com/openai/v1"
            self.openai_compatible_client = OpenAI(base_url=base_url, api_key=self.api_key or CONFIG.GROQ_API_KEY)

        elif self.provider == "ollama" and OpenAI:
            base_url = "http://localhost:11434/v1"
            self.openai_compatible_client = OpenAI(base_url=base_url, api_key="ollama")

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        tool_definition: Dict[str, Any],
        max_tokens: int = 2500
    ) -> Dict[str, Any]:
        """
        Executes a structured tool/function call across Anthropic or NVIDIA NIM / OpenAI APIs.
        """
        # 1. Anthropic Route
        if self.provider == "anthropic":
            if not self.anthropic_client:
                return {"error": "Anthropic API key not configured"}

            api_kwargs = get_model_api_kwargs(model=self.model, max_tokens=max_tokens)
            tool_name = tool_definition.get("name", "submit_decision")

            resp = self.anthropic_client.messages.create(
                **api_kwargs,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[tool_definition],
                tool_choice={"type": "tool", "name": tool_name}
            )

            for block in resp.content:
                if block.type == "tool_use" and block.name == tool_name:
                    return block.input
            return {"error": "No tool call returned by Claude"}

        # 2. NVIDIA NIM / OpenAI Compatible Route
        elif self.provider in ["nvidia", "groq", "ollama"]:
            if not self.openai_compatible_client:
                return {"error": f"{self.provider.upper()} client not initialized"}

            # Build JSON output instructions
            schema_json = json.dumps(tool_definition.get("input_schema", {}), indent=2)
            formatted_prompt = (
                f"{user_prompt}\n\n"
                f"You MUST respond ONLY with a valid JSON object matching this schema (do not include Markdown backticks or explanation outside the JSON):\n"
                f"{schema_json}"
            )

            models_to_try = [
                self.model,
                "meta/llama-3.2-11b-vision-instruct"
            ]

            last_err = "No response"
            for m in dict.fromkeys(models_to_try):
                call_kwargs = {
                    "model": m,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": formatted_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": max_tokens,
                    "stream": False,
                    "timeout": 3.0
                }

                if "deepseek" in m.lower():
                    call_kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}}
                    call_kwargs["temperature"] = 0.7

                try:
                    completion = self.openai_compatible_client.chat.completions.create(**call_kwargs)
                    message = completion.choices[0].message
                    
                    reasoning = getattr(message, "reasoning", None) or getattr(message, "reasoning_content", None)
                    content = message.content.strip() if message.content else ""

                    if "{" in content and "}" in content:
                        json_str = content[content.find("{"):content.rfind("}")+1]
                        data = json.loads(json_str)
                        if reasoning and "detailed_reasoning" in data and not data.get("detailed_reasoning"):
                            data["detailed_reasoning"] = str(reasoning)[:500]
                        return data

                    last_err = f"Model {m} returned non-JSON content: {content[:100]}"
                except Exception as e:
                    last_err = f"Model {m} error: {str(e)}"
                    break  # Failover immediately to algorithmic consensus

            return {"error": last_err}

        return {"error": f"Unknown provider: {self.provider}"}

    def call_chat(
        self,
        system_prompt: str,
        user_prompt: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 120,
        temperature: float = 0.35
    ) -> Optional[str]:
        """
        Executes a fast natural conversational completion across Anthropic Claude or NVIDIA NIM.
        Returns cleaned text ready for voice synthesis and chat response.
        """
        chat_msgs = []
        if messages:
            chat_msgs = list(messages)
        elif user_prompt:
            chat_msgs = [{"role": "user", "content": user_prompt}]

        # 1. Anthropic Route
        if self.provider == "anthropic" and self.anthropic_client:
            try:
                resp = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=chat_msgs
                )
                text_blocks = [b.text for b in resp.content if hasattr(b, "text")]
                ans = " ".join(text_blocks).strip()
                return ans.replace("*", "").replace("#", "").replace("`", "").strip()
            except Exception:
                pass

        # 2. NVIDIA NIM / OpenAI Compatible Route
        elif self.openai_compatible_client:
            models_to_try = [
                self.model,
                "meta/llama-3.2-11b-vision-instruct",
                "deepseek-ai/deepseek-v4-flash-0731"
            ]

            full_messages = [{"role": "system", "content": system_prompt}] + chat_msgs

            for m in dict.fromkeys(models_to_try):
                try:
                    kwargs = {
                        "model": m,
                        "messages": full_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "timeout": 5.0
                    }
                    completion = self.openai_compatible_client.chat.completions.create(**kwargs)
                    msg = completion.choices[0].message
                    content = msg.content or getattr(msg, "reasoning_content", None) or ""
                    clean_content = content.strip().replace("*", "").replace("```", "").replace("#", "").replace("`", "").strip()
                    if clean_content:
                        return clean_content
                except Exception:
                    continue

        return None



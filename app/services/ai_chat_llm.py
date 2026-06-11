from __future__ import annotations

import json
from typing import Any

from openai import AuthenticationError, BadRequestError, NotFoundError, OpenAI, PermissionDeniedError

from app.core.config import (
    OPENAI_API_KEY,
    OPENAI_CHAT_MAX_TOKENS,
    OPENAI_CHAT_MODEL,
    OPENAI_CHAT_TEMPERATURE,
)

MEAL_MENTOR_CHAT_SYSTEM_PROMPT = """
Ты Meal-Mentor — ИИ-помощник по анализу дневника питания.

Твоя задача:
- помогать пользователю понимать его рацион;
- анализировать данные дневника питания, веса, воды, активности и добавок;
- замечать мягкие паттерны: недобор белка, перебор жиров, низкая клетчатка, нерегулярное питание, недостаток воды, частые калорийные перекусы;
- давать общие, осторожные и практичные рекомендации.

Ограничения:
- не ставь диагнозы;
- не назначай лечение;
- не интерпретируй медицинские анализы как врач;
- не обещай гарантированный результат;
- не используй формулировки “точно”, “обязательно”, “вылечит”, “гарантированно”;
- не рекомендуй резкие диеты, голодание, экстремальное снижение калорий или опасные практики;
- по вопросам заболеваний, лекарств, анализов, беременности, расстройств пищевого поведения, резкого изменения веса или плохого самочувствия направляй к врачу/специалисту.

Стиль:
- говори дружелюбно, спокойно и понятно;
- не стыди пользователя за еду;
- не пугай;
- давай 1–3 конкретных шага;
- если данных мало, честно скажи, что вывод предварительный;
- если данных нет, помоги пользователю начать вести дневник;
- отвечай на русском языке, если пользователь не попросил другой язык.
""".strip()

WELCOME_USER_MESSAGE = """
Сформируй первое короткое приветствие для пользователя Meal-Mentor на основе контекста.
Если данных питания нет — общайся как с новым пользователем.
Если история питания есть — кратко отметь 1–2 мягких наблюдения.
Не делай медицинских выводов.
Не больше 2–4 коротких абзацев.
""".strip()


class AiChatLlmError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def build_context_message(context: dict) -> str:
    return (
        "Ниже JSON-контекст пользователя из базы Meal-Mentor. "
        "Используй его только как справочную информацию. "
        "Не показывай JSON пользователю. "
        "Не выдумывай отсутствующие данные. "
        "Если данных недостаточно — скажи об этом мягко. "
        "Если в context.risk_context medical_risk_detected=true, отвечай только в формате общей поддержки "
        "и рекомендуй обратиться к квалифицированному специалисту.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )


def _client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)


def _usage_metadata(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    return {
        "model": OPENAI_CHAT_MODEL,
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
    }


def _is_gpt5_model(model: str) -> bool:
    return model.lower().startswith("gpt-5")


def _create_completion(messages: list[dict]) -> Any:
    base_kwargs: dict[str, Any] = {
        "model": OPENAI_CHAT_MODEL,
        "messages": messages,
        "max_completion_tokens": OPENAI_CHAT_MAX_TOKENS,
    }
    if not _is_gpt5_model(OPENAI_CHAT_MODEL):
        base_kwargs["temperature"] = OPENAI_CHAT_TEMPERATURE

    try:
        return _client().chat.completions.create(**base_kwargs)
    except BadRequestError as exc:
        text = str(exc).lower()
        if "max_completion_tokens" in text and ("unsupported" in text or "unrecognized" in text):
            retry_kwargs = dict(base_kwargs)
            retry_kwargs.pop("max_completion_tokens", None)
            retry_kwargs["max_tokens"] = OPENAI_CHAT_MAX_TOKENS
            return _client().chat.completions.create(**retry_kwargs)
        if "temperature" in text and ("unsupported" in text or "only the default" in text):
            retry_kwargs = dict(base_kwargs)
            retry_kwargs.pop("temperature", None)
            return _client().chat.completions.create(**retry_kwargs)
        raise AiChatLlmError("bad_request", str(exc)) from exc
    except AuthenticationError as exc:
        raise AiChatLlmError("auth_error", "OpenAI authentication failed") from exc
    except PermissionDeniedError as exc:
        raise AiChatLlmError("permission_denied", "OpenAI model or project permission denied") from exc
    except NotFoundError as exc:
        raise AiChatLlmError("model_not_found", f"OpenAI model is unavailable: {OPENAI_CHAT_MODEL}") from exc


def _generate(*, user_message: str, context: dict, previous_messages: list[dict]) -> tuple[str, dict]:
    messages = [
        {"role": "system", "content": MEAL_MENTOR_CHAT_SYSTEM_PROMPT},
        {"role": "system", "content": build_context_message(context)},
    ]
    messages.extend(previous_messages[-20:])
    messages.append({"role": "user", "content": user_message})

    response = _create_completion(messages)
    choice = response.choices[0] if response.choices else None
    content = choice.message.content.strip() if choice and choice.message and choice.message.content else ""
    if not content:
        raise RuntimeError("Empty AI chat response")
    return content, _usage_metadata(response)


def generate_ai_chat_reply(
    *,
    user_message: str,
    context: dict,
    previous_messages: list[dict],
) -> tuple[str, dict]:
    return _generate(user_message=user_message, context=context, previous_messages=previous_messages)


def generate_ai_chat_welcome(context: dict) -> tuple[str, dict]:
    return _generate(user_message=WELCOME_USER_MESSAGE, context=context, previous_messages=[])

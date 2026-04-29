"""
Анализ состава по фото этикетки (OpenAI vision). Без БД, без meal-пайплайна.
Промпт: data/promt3.txt (читается при каждом запросе).
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import DATA_DIR, OPENAI_API_KEY, OPENAI_MODEL


def _prompt_file_path() -> Path:
    return Path(DATA_DIR) / "promt3.txt"


def load_label_prompt() -> str:
    path = _prompt_file_path()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Достаёт первый JSON-объект из ответа (markdown ```json, лишний текст)."""
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(raw, start)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _data_url_for_bytes(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{b64}"


def analyze_label_from_image_bytes(image_bytes: bytes) -> dict[str, Any]:
    """
    Vision + promt3.txt → dict по схеме промпта или служебный статус.
    Не пишет в БД.
    """
    if not OPENAI_API_KEY:
        return {
            "status": "error",
            "error": "OPENAI_API_KEY is not set",
        }
    prompt = load_label_prompt()
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
    image_url = _data_url_for_bytes(image_bytes)
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=2048,
            temperature=0.2,
        )
        choice = resp.choices[0] if resp.choices else None
        content = (choice.message.content or "").strip() if choice and choice.message else ""
        if not content:
            return {"status": "error", "error": "Пустой ответ модели"}
        parsed = extract_json_object(content)
        if parsed is None:
            return {
                "status": "parse_error",
                "error": "Не удалось разобрать JSON в ответе модели",
                "raw_preview": content[:400],
            }
        return parsed
    except Exception as e:
        return {"status": "error", "error": str(e)}


def format_label_result_for_telegram(data: dict[str, Any]) -> str:
    """Текст сообщения для Telegram по правилам ТЗ."""
    status = (data.get("status") or "").strip().lower()

    if status == "no_label":
        return "❌ Не вижу этикетку с составом. Попробуй сфотографировать ближе."

    if status == "unreadable":
        return "😕 Не удалось прочитать состав. Попробуй сделать фото четче."

    if status == "parse_error":
        return "Не удалось разобрать ответ. Попробуй ещё раз или смени ракурс фото."

    if status == "error":
        err = data.get("error") or "Неизвестная ошибка"
        return f"Сервис временно недоступен: {err}"

    if status != "ok":
        return f"Не удалось обработать результат (статус: {status or 'неизвестно'}). Попробуй ещё раз."

    assessment = data.get("overall_assessment")
    assessment_s = str(assessment).strip() if assessment is not None else "—"

    warnings = data.get("warnings") or []
    if not isinstance(warnings, list):
        warnings = []
    positives = data.get("positives") or []
    if not isinstance(positives, list):
        positives = []

    summary = (data.get("summary") or "").strip() or "—"

    lines: list[str] = ["🧾 Анализ состава"]
    pname = data.get("product_name")
    ing_text = data.get("ingredients_text")
    if pname:
        lines.append(f"📦 {pname}")
    if ing_text and isinstance(ing_text, str):
        it = ing_text.strip()
        if len(it) > 800:
            it = it[:800] + "…"
        lines.append(f"📝 Состав с этикетки: {it}")
    lines.extend(
        [
            "",
            f"📊 Оценка: {assessment_s}",
            "",
            "⚠️ Что смущает:",
        ]
    )
    if warnings:
        for w in warnings:
            if w:
                lines.append(f"• {w}")
    else:
        lines.append("• —")

    lines.append("")
    lines.append("✅ Что нормально:")
    if positives:
        for p in positives:
            if p:
                lines.append(f"• {p}")
    else:
        lines.append("• —")

    additives = data.get("detected_e_additives") or []
    if isinstance(additives, list) and additives:
        lines.append("")
        lines.append("🏷 Е-добавки:")
        for ad in additives[:12]:
            if not isinstance(ad, dict):
                continue
            code = ad.get("code") or ""
            name = ad.get("name") or ""
            risk = ad.get("risk_level") or ""
            lines.append(f"• {code} {name} — {risk}".strip())

    lines.append("")
    lines.append("🧠 Вывод:")
    lines.append(summary)

    return "\n".join(lines)

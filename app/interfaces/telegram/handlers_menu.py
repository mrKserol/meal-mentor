"""
Main menu, onboarding, diary/profile/subscription (Telegram UI only).
"""

from __future__ import annotations

import logging
from datetime import date
from io import BytesIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, filters
from telegram.ext import MessageHandler

from app.interfaces.telegram.inline_calendar import birth_date_calendar_keyboard
from app.interfaces.telegram.states import USER_STATES, FlowState, UIMode
from app.interfaces.telegram import tg_api
from app.interfaces.telegram.telegram_formatters import (
    format_add_meal_prompt,
    format_diary_intro,
    format_profile_card,
    format_weight_correction_intro,
    format_weight_monitoring_intro,
)

logger = logging.getLogger(__name__)

_BLOCKED_IF_INCOMPLETE_PREFIXES = (
    "m:diary",
    "m:prof",
    "m:sub:tariffs",
    "m:sub:mine",
    "m:sub:order:",
)


def _name(u) -> str:
    if not u:
        return "друг"
    return (u.first_name or u.username or "друг").strip() or "друг"


def _ensure_registered(telegram_id: int, username: str | None, first_name: str | None) -> None:
    try:
        tg_api.post_json(
            "/users/register",
            {"telegram_id": telegram_id, "username": username, "first_name": first_name},
        )
    except Exception as e:
        logger.warning("register failed: %s", e)


def _profile(telegram_id: int) -> dict:
    return tg_api.get_json("/users/profile", params={"telegram_id": telegram_id})


def _has_active_sub(telegram_id: int) -> bool:
    try:
        st = tg_api.get_json("/subscriptions/status", params={"telegram_id": telegram_id})
        return bool(st.get("active"))
    except Exception:
        return False


def _is_blocked_incomplete(data: str, pr: dict) -> bool:
    if pr.get("profile_complete"):
        return False
    if data.startswith(_BLOCKED_IF_INCOMPLETE_PREFIXES):
        return True
    if data == "m:main":
        return False
    return False


def kb_onboarding() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Пол", callback_data="m:onb:sex"),
                InlineKeyboardButton("Дата рождения", callback_data="m:onb:bd"),
            ],
            [
                InlineKeyboardButton("Рост", callback_data="m:onb:height"),
                InlineKeyboardButton("Вес", callback_data="m:onb:weight"),
            ],
            [
                InlineKeyboardButton("Желаемый вес", callback_data="m:onb:tweight"),
                InlineKeyboardButton("Активность", callback_data="m:onb:act"),
            ],
        ]
    )


def kb_main(*, sub_active: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Дневник питания", callback_data="m:diary")],
        [InlineKeyboardButton("Мой профиль", callback_data="m:prof")],
    ]
    if sub_active:
        rows.append([InlineKeyboardButton("Моя подписка", callback_data="m:sub:mine")])
    else:
        rows.append([InlineKeyboardButton("Тарифы подписок", callback_data="m:sub:tariffs")])
    return InlineKeyboardMarkup(rows)


def kb_meal_add_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ В дневник", callback_data="m:diary")]])


def enter_add_meal_flow(telegram_user_id: int) -> None:
    """Единый вход в сценарий добавления приёма (кнопка «Добавить приём пищи», /add_meal). Сбрасывает локальное UI-состояние пользователя."""
    USER_STATES[telegram_user_id] = {
        "mode": UIMode.DIARY_ADD_MEAL,
        "state": FlowState.MEAL_ADD_WAITING_INPUT,
    }


def kb_diary() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Добавить приём пищи", callback_data="m:diary:add")],
            [InlineKeyboardButton("История приёмов пищи", callback_data="m:diary:hist")],
            [InlineKeyboardButton("Статистика питания", callback_data="m:diary:stats")],
            [InlineKeyboardButton("Редактировать цель", callback_data="m:dw:goal")],
            [InlineKeyboardButton("Актуальный вес", callback_data="m:dw:weight")],
            [InlineKeyboardButton("Динамика веса", callback_data="m:diary:chart")],
            [InlineKeyboardButton("Рекомендуемые нормы", callback_data="m:diary:norms")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")],
        ]
    )


def kb_profile_root() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Изменить информацию", callback_data="m:prof:edit")],
            [InlineKeyboardButton("⬅ Назад в главное меню", callback_data="m:main")],
        ]
    )


def kb_diary_weight_root() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Коррекция веса", callback_data="m:dw:fix")],
            [InlineKeyboardButton("⬅ Назад", callback_data="m:diary")],
        ]
    )


def kb_sex() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Мужской", callback_data="m:set:sex:male"),
                InlineKeyboardButton("Женский", callback_data="m:set:sex:female"),
            ],
            [InlineKeyboardButton("⬅ Назад", callback_data="m:onb:back")],
        ]
    )


def kb_activity() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("1 — низкая", callback_data="m:set:act:1.0")],
            [InlineKeyboardButton("1.3 — средняя", callback_data="m:set:act:1.3")],
            [InlineKeyboardButton("1.5 — высокая", callback_data="m:set:act:1.5")],
            [InlineKeyboardButton("⬅ Назад", callback_data="m:onb:back")],
        ]
    )


def kb_tariffs() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("1 неделя — 70 ₽", callback_data="m:sub:order:tariff_1w")],
            [InlineKeyboardButton("2 недели — 126 ₽", callback_data="m:sub:order:tariff_2w")],
            [InlineKeyboardButton("1 месяц — 210 ₽", callback_data="m:sub:order:tariff_1m")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")],
        ]
    )


async def _send_main_if_complete(context: ContextTypes.DEFAULT_TYPE, uid: int, chat_id: int) -> None:
    pr = _profile(uid)
    if not pr.get("profile_complete"):
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text="Профиль заполнен. Добро пожаловать в главное меню!",
        reply_markup=kb_main(sub_active=_has_active_sub(uid)),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    u = update.effective_user
    _ensure_registered(u.id, u.username, u.first_name)
    try:
        pr = _profile(u.id)
    except Exception as e:
        logger.exception("profile fetch: %s", e)
        await update.message.reply_text("Не удалось связаться с сервером. Проверь BASE_URL и запуск API.")
        return
    complete = pr.get("profile_complete")
    nm = _name(u)
    USER_STATES[u.id] = {"mode": UIMode.IDLE}
    if not complete:
        text = (
            f"Добро пожаловать, {nm}! Заполни профиль, чтобы определить цель и вести корректный расчёт.\n"
            "Выберите нужную функцию из меню ниже."
        )
        await update.message.reply_text(text, reply_markup=kb_onboarding())
        return
    text = (
        f"Привет, {nm}! Я Meal Mentor — помогу оценить состав и калорийность еды по фото, "
        "буду вести дневник питания и дам рекомендации для достижения твоей цели."
    )
    sub = _has_active_sub(u.id)
    await update.message.reply_text(text, reply_markup=kb_main(sub_active=sub))


async def cmd_add_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    u = update.effective_user
    _ensure_registered(u.id, u.username, u.first_name)
    try:
        pr = _profile(u.id)
    except Exception as e:
        logger.exception("profile fetch: %s", e)
        await update.message.reply_text("Не удалось связаться с сервером. Проверь BASE_URL и запуск API.")
        return
    if not pr.get("profile_complete"):
        await update.message.reply_text(
            "Сначала заполни профиль, чтобы я мог корректно рассчитывать показатели.",
            reply_markup=kb_onboarding(),
        )
        return
    enter_add_meal_flow(u.id)
    await update.message.reply_text(format_add_meal_prompt(extended=False), reply_markup=kb_meal_add_back())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data or not update.effective_user:
        return
    uid = update.effective_user.id
    data = q.data
    uname = update.effective_user.username
    fname = update.effective_user.first_name

    try:
        if data.startswith("c:"):
            await _handle_calendar(q, uid, data, context)
            return

        pr = _profile(uid)
        if _is_blocked_incomplete(data, pr):
            await q.answer("Сначала заполни профиль полностью.", show_alert=True)
            await q.edit_message_text(
                f"{_name(update.effective_user)}, осталось заполнить профиль.",
                reply_markup=kb_onboarding(),
            )
            return

        await q.answer()
        await _dispatch_menu(q, uid, uname, fname, data, context, pr)
    except Exception as e:
        logger.exception("menu %s: %s", data, e)
        await context.bot.send_message(chat_id=uid, text="Ошибка запроса к серверу. Попробуй позже.")


async def _handle_calendar(q, uid: int, data: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    if data == "c:x":
        await q.answer()
        return
    today = date.today()
    if data.startswith("c:p:"):
        ym = data.split(":", 2)[-1]
        y, mo = ym.split("-")
        await q.edit_message_text(
            "Выберите дату рождения:",
            reply_markup=birth_date_calendar_keyboard(int(y), int(mo)),
        )
        await q.answer()
        return
    if data.startswith("c:n:"):
        ym = data.split(":", 2)[-1]
        y, mo = ym.split("-")
        await q.edit_message_text(
            "Выберите дату рождения:",
            reply_markup=birth_date_calendar_keyboard(int(y), int(mo)),
        )
        await q.answer()
        return
    if data.startswith("c:d:"):
        dstr = data.split(":", 2)[-1]
        bd = date.fromisoformat(dstr)
        if bd > today:
            await q.answer("Нельзя выбрать дату в будущем", show_alert=True)
            return
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "birth_date": bd.isoformat()})
        await q.edit_message_text("Дата рождения сохранена.", reply_markup=kb_onboarding())
        await _send_main_if_complete(context, uid, q.message.chat_id)
        await q.answer()
        return


async def _dispatch_menu(q, uid: int, uname: str | None, fname: str | None, data: str, context, pr: dict) -> None:
    if data == "m:main":
        USER_STATES[uid] = {"mode": UIMode.IDLE}
        pr = _profile(uid)
        nm = fname or uname or "друг"
        if not pr.get("profile_complete"):
            await q.edit_message_text(
                f"Добро пожаловать, {nm}! Заполни профиль.\nВыбери пункт:",
                reply_markup=kb_onboarding(),
            )
            return
        await q.edit_message_text(
            f"Главное меню, {nm}.",
            reply_markup=kb_main(sub_active=_has_active_sub(uid)),
        )
        return

    if data == "m:onb:back":
        await q.edit_message_text("Заполнение профиля — выбери поле:", reply_markup=kb_onboarding())
        return

    if data == "m:onb:sex":
        await q.edit_message_text("Выберите пол:", reply_markup=kb_sex())
        return
    if data.startswith("m:set:sex:"):
        sex = "male" if data.endswith(":male") else "female"
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "sex": sex})
        await q.edit_message_text("Пол сохранён.", reply_markup=kb_onboarding())
        await _send_main_if_complete(context, uid, q.message.chat_id)
        return

    if data == "m:onb:act":
        await q.edit_message_text("Уровень физической активности:", reply_markup=kb_activity())
        return
    if data.startswith("m:set:act:"):
        kfa = data.split(":")[-1]
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "activity_level": kfa})
        await q.edit_message_text("Активность сохранена.", reply_markup=kb_onboarding())
        await _send_main_if_complete(context, uid, q.message.chat_id)
        return

    if data == "m:onb:bd":
        t = date.today()
        await q.edit_message_text(
            "Выберите дату рождения:",
            reply_markup=birth_date_calendar_keyboard(t.year, t.month),
        )
        return

    if data == "m:onb:height":
        USER_STATES.setdefault(uid, {})["awaiting_field"] = "height_cm"
        await q.edit_message_text("Укажите ваш рост в сантиметрах (например: 175). Напишите числом в чат.")
        return
    if data == "m:onb:weight":
        USER_STATES.setdefault(uid, {})["awaiting_field"] = "weight_kg"
        await q.edit_message_text("Укажите ваш текущий вес в килограммах (например: 70.5). Напишите в чат.")
        return
    if data == "m:onb:tweight":
        USER_STATES.setdefault(uid, {})["awaiting_field"] = "target_weight_kg"
        USER_STATES[uid]["edit_target_from"] = "onboarding"
        await q.edit_message_text("Укажите желаемый вес в килограммах (например: 60). Напишите в чат.")
        return

    if data == "m:diary":
        USER_STATES.setdefault(uid, {})["mode"] = UIMode.IDLE
        for k in ("state", "meal_data", "context"):
            USER_STATES[uid].pop(k, None)
        await q.edit_message_text(format_diary_intro(), reply_markup=kb_diary())
        return

    if data == "m:diary:add":
        enter_add_meal_flow(uid)
        await q.edit_message_text(
            format_add_meal_prompt(extended=True),
            reply_markup=kb_meal_add_back(),
        )
        return

    if data == "m:diary:stats":
        png = tg_api.get_bytes("/nutrition/stats/chart", params={"telegram_id": uid, "days": 7})
        await q.message.reply_photo(photo=BytesIO(png), caption="Статистика за 7 дней (ккал и БЖУ).")
        await q.message.reply_text(format_diary_intro(), reply_markup=kb_diary())
        return
    if data == "m:diary:norms":
        info = tg_api.get_json("/nutrition/recommended", params={"telegram_id": uid})
        if info.get("status") != "ok":
            await q.message.reply_text(info.get("message", "Недостаточно данных для расчёта нормы."))
        else:
            await q.message.reply_text(
                f"Рекомендуемая норма (оценка):\n"
                f"Калории: {info['calories_kcal']:.0f} ккал/день\n"
                f"Белки: {info['protein_g']} г | Жиры: {info['fat_g']} г | Углеводы: {info['carbs_g']} г\n"
                f"(БЖУ: 20% / 30% / 50%; КФА={info['activity_multiplier']})"
            )
        await q.message.reply_text(format_diary_intro(), reply_markup=kb_diary())
        return

    if data == "m:diary:chart":
        for period, title in (("week", "недели"), ("month", "месяца")):
            png = tg_api.get_bytes("/users/weights/chart", params={"telegram_id": uid, "period": period})
            await q.message.reply_photo(photo=BytesIO(png), caption=f"Динамика веса ({title})")
        await q.message.reply_text(format_diary_intro(), reply_markup=kb_diary())
        return

    if data == "m:dw:goal":
        USER_STATES.setdefault(uid, {})["awaiting_field"] = "target_weight_kg"
        USER_STATES[uid]["edit_target_from"] = "diary"
        await q.edit_message_text(
            f"Текущая цель: {(_profile(uid).get('user') or {}).get('target_weight_kg') or '—'} кг.\n"
            "Введи новый желаемый вес в кг (число).",
        )
        return

    if data == "m:dw:weight":
        await q.edit_message_text(format_weight_monitoring_intro(), reply_markup=kb_diary_weight_root())
        return
    if data == "m:dw:fix":
        USER_STATES.setdefault(uid, {})["awaiting_field"] = "weight_correction"
        USER_STATES[uid]["weight_fix_from"] = "diary"
        await q.edit_message_text(format_weight_correction_intro())
        return
    if data == "m:dw:undo":
        try:
            tg_api.delete("/users/weights/latest", params={"telegram_id": uid})
            await q.edit_message_text("Последнее взвешивание удалено.")
        except Exception:
            await q.edit_message_text("Не удалось удалить (возможно, записей нет).")
        await q.message.reply_text(format_weight_monitoring_intro(), reply_markup=kb_diary_weight_root())
        return

    if data == "m:diary:hist":
        USER_STATES.setdefault(uid, {})["hist_off"] = 0
        await _show_history_page(q.message, uid, 0)
        return
    if data.startswith("m:ho:"):
        off = int(data.split(":")[-1])
        USER_STATES.setdefault(uid, {})["hist_off"] = off
        await _show_history_page(q.message, uid, off)
        return
    if data.startswith("m:hv:"):
        mid = int(data.split(":")[-1])
        text, kb = _meal_detail_text_and_kb(uid, mid)
        await q.message.reply_text(text, reply_markup=kb)
        return
    if data.startswith("m:hdi:"):
        parts = data.split(":")
        mid, iid = int(parts[2]), int(parts[3])
        tg_api.delete(f"/meals/{mid}/items/{iid}", params={"telegram_id": uid})
        try:
            text, kb = _meal_detail_text_and_kb(uid, mid)
            await q.edit_message_text(text, reply_markup=kb)
        except Exception as e:
            logger.warning("meal detail refresh after item delete: %s", e)
            await q.edit_message_text(
                "Ингредиент удалён.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("К истории", callback_data="m:diary:hist")]]),
            )
        return
    if data.startswith("m:hai:"):
        mid = int(data.split(":")[-1])
        st = USER_STATES.setdefault(uid, {})
        st["mode"] = UIMode.IDLE
        for k in ("state", "meal_data", "context"):
            st.pop(k, None)
        st["awaiting_field"] = f"histadd:{mid}"
        await q.edit_message_text("Введи продукт и вес (например: «гречка 150 г» или «яблоко 200»).")
        return

    if data.startswith("m:hd:") and not data.startswith("m:hdc:"):
        mid = int(data.split(":")[-1])
        await q.message.reply_text(
            "Удалить весь приём?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Да, удалить", callback_data=f"m:hdc:{mid}"),
                        InlineKeyboardButton("Отмена", callback_data="m:diary:hist"),
                    ]
                ]
            ),
        )
        return
    if data.startswith("m:hdc:"):
        mid = int(data.split(":")[-1])
        tg_api.delete(f"/meals/{mid}", params={"telegram_id": uid})
        await q.edit_message_text("Запись удалена.")
        await _show_history_page(q.message, uid, USER_STATES.get(uid, {}).get("hist_off", 0))
        return
    if data.startswith("m:he:"):
        parts = data.split(":")
        if len(parts) < 4:
            await context.bot.send_message(chat_id=q.message.chat_id, text="Некорректная команда.")
            return
        mid, iid = int(parts[2]), int(parts[3])
        USER_STATES.setdefault(uid, {})["awaiting_field"] = f"editw:{mid}:{iid}"
        await q.edit_message_text("Введите новый вес порции в граммах (целое число).")
        return

    if data == "m:prof":
        USER_STATES.setdefault(uid, {})["mode"] = UIMode.IDLE
        u = pr.get("user") or {}
        card = format_profile_card(
            username=u.get("username"),
            first_name=fname,
            sex=u.get("sex"),
            birth_date=u.get("birth_date"),
            height_cm=u.get("height_cm"),
            weight_kg=u.get("weight_kg"),
        )
        await q.edit_message_text(card, reply_markup=kb_profile_root())
        return
    if data == "m:prof:edit":
        await q.edit_message_text("Что изменить?", reply_markup=kb_onboarding())
        return

    if data == "m:sub:tariffs":
        await q.edit_message_text(
            "Выберите тариф для доступа ко всем функциям.\nПровайдер: Robokassa (оплата подключается позже).",
            reply_markup=kb_tariffs(),
        )
        return
    if data == "m:sub:mine":
        st = tg_api.get_json("/subscriptions/status", params={"telegram_id": uid})
        if not st.get("active"):
            await q.edit_message_text("Активной подписки нет.", reply_markup=kb_tariffs())
            return
        s = st["subscription"]
        await q.edit_message_text(
            f"План: {s.get('plan')}\nДо: {s.get('ends_at')}\nСтатус оплаты: {s.get('payment_status')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")]]),
        )
        return
    if data.startswith("m:sub:order:"):
        plan = data.split(":")[-1]
        out = tg_api.post_json("/subscriptions/order", {"telegram_id": uid, "plan": plan})
        await q.edit_message_text(
            f"Заявка создана ({plan}). Статус: {out.get('status')}.\n{out.get('message', '')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")]]),
        )
        return


def _meal_detail_text_and_kb(uid: int, mid: int) -> tuple[str, InlineKeyboardMarkup]:
    detail = tg_api.get_json(f"/meals/{mid}", params={"telegram_id": uid})
    lines = [f"Приём #{detail['id']} {detail['meal_datetime']}", f"Источник: {detail.get('source_type')}"]
    kb_rows: list[list[InlineKeyboardButton]] = []
    for it in detail.get("items") or []:
        lines.append(f"• {it['item_name']}: {it.get('estimated_weight_g')} г")
        label = (it["item_name"][:16] + "…") if len(it["item_name"]) > 16 else it["item_name"]
        kb_rows.append(
            [
                InlineKeyboardButton(f"Вес {label}", callback_data=f"m:he:{mid}:{it['id']}"),
                InlineKeyboardButton("✕", callback_data=f"m:hdi:{mid}:{it['id']}"),
            ]
        )
    kb_rows.append([InlineKeyboardButton("+ Добавить ингредиент", callback_data=f"m:hai:{mid}")])
    kb_rows.append([InlineKeyboardButton("Удалить приём", callback_data=f"m:hd:{mid}")])
    kb_rows.append([InlineKeyboardButton("К истории", callback_data="m:diary:hist")])
    return "\n".join(lines), InlineKeyboardMarkup(kb_rows)


async def _show_history_page(message, uid: int, offset: int) -> None:
    data = tg_api.get_json("/meals/list", params={"telegram_id": uid, "limit": 5, "offset": offset})
    items = data.get("items") or []
    if not items:
        await message.reply_text("Пока нет сохранённых приёмов пищи.", reply_markup=kb_diary())
        return
    rows = []
    for m in items:
        rows.append([InlineKeyboardButton(f"#{m['id']} {m['meal_datetime'][:16]}", callback_data=f"m:hv:{m['id']}")])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅", callback_data=f"m:ho:{max(0, offset - 5)}"))
    if len(items) >= 5:
        nav.append(InlineKeyboardButton("➡", callback_data=f"m:ho:{offset + 5}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅ Дневник", callback_data="m:diary")])
    await message.reply_text("История приёмов пищи:", reply_markup=InlineKeyboardMarkup(rows))


class AwaitingNumericFilter(filters.MessageFilter):
    def filter(self, message):
        u = message.from_user
        if not u or not message.text:
            return False
        st = USER_STATES.get(u.id) or {}
        return bool(st.get("awaiting_field"))


awaiting_numeric_filter = AwaitingNumericFilter()


async def handle_profile_numeric(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    st = USER_STATES.get(uid) or {}
    field = st.get("awaiting_field")
    if not field:
        return
    text = update.message.text.strip()

    if field.startswith("histadd:"):
        mid = int(field.split(":")[-1])
        st.pop("awaiting_field", None)
        try:
            out = tg_api.post_json(
                f"/meals/{mid}/items",
                {"telegram_id": uid, "description": text},
            )
            await update.message.reply_text(
                f"Добавлено строк: {out.get('items_added', 0)}.",
                reply_markup=kb_diary(),
            )
        except Exception as e:
            logger.warning("hist add: %s", e)
            await update.message.reply_text("Не удалось добавить. Попробуй другую формулировку.", reply_markup=kb_diary())
        return

    st.pop("awaiting_field", None)

    if field == "height_cm":
        try:
            v = int(text)
            if v < 50 or v > 260:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Неверное значение! Введите корректное число.")
            st["awaiting_field"] = "height_cm"
            return
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "height_cm": v})
        await update.message.reply_text("Рост сохранён.", reply_markup=kb_onboarding())
        await _send_main_if_complete(context, uid, update.effective_chat.id)
        return

    if field == "weight_kg":
        try:
            v = float(text.replace(",", "."))
            if v <= 0 or v > 400:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Неверное значение! Введите корректное число.")
            st["awaiting_field"] = "weight_kg"
            return
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "weight_kg": v})
        await update.message.reply_text("Вес сохранён.", reply_markup=kb_onboarding())
        await _send_main_if_complete(context, uid, update.effective_chat.id)
        return

    if field == "target_weight_kg":
        try:
            v = float(text.replace(",", "."))
            if v <= 0 or v > 400:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Неверное значение! Введите корректное число.")
            st["awaiting_field"] = "target_weight_kg"
            return
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "target_weight_kg": v})
        src = USER_STATES.get(uid, {}).pop("edit_target_from", "onboarding")
        reply_kb = kb_diary() if src == "diary" else kb_onboarding()
        await update.message.reply_text("Желаемый вес сохранён.", reply_markup=reply_kb)
        await _send_main_if_complete(context, uid, update.effective_chat.id)
        return

    if field == "weight_correction":
        try:
            v = float(text.replace(",", "."))
            if v <= 0 or v > 400:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Неверное значение! Введите корректное число.")
            st["awaiting_field"] = "weight_correction"
            return
        tg_api.post_json("/users/weights", {"telegram_id": uid, "weight_kg": v})
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "weight_kg": v})
        src = USER_STATES.get(uid, {}).pop("weight_fix_from", "diary")
        reply_kb = kb_diary_weight_root() if src == "diary" else kb_onboarding()
        await update.message.reply_text("Вес записан.", reply_markup=reply_kb)
        return

    if field.startswith("editw:"):
        parts = field.split(":")
        mid, iid = int(parts[1]), int(parts[2])
        try:
            w = int(float(text))
            if w <= 0:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Неверное значение! Введите целое число граммов.")
            st["awaiting_field"] = field
            return
        tg_api.patch_params(f"/meals/{mid}/items/{iid}", {"telegram_id": uid, "weight_g": w})
        await update.message.reply_text(
            "Вес позиции обновлён.",
            reply_markup=kb_diary(),
        )


async def photo_outside_diary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Чтобы добавить приём пищи: «Дневник питания» → «Добавить приём пищи», затем отправь фото или текст."
        )


def build_profile_numeric_handler() -> MessageHandler:
    return MessageHandler(awaiting_numeric_filter & filters.TEXT & ~filters.COMMAND, handle_profile_numeric)

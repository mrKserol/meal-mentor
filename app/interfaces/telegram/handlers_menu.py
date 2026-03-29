"""
Main menu, onboarding, diary/profile/subscription sections (Telegram UI only).
"""

from __future__ import annotations

import logging
from datetime import date
from io import BytesIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, filters
from telegram.ext import MessageHandler

from app.interfaces.telegram.states import USER_STATES, UIMode
from app.interfaces.telegram import tg_api

logger = logging.getLogger(__name__)


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


def kb_back_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")]])


def kb_diary() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Добавить приём пищи", callback_data="m:diary:add")],
            [InlineKeyboardButton("Статистика питания", callback_data="m:diary:stats")],
            [InlineKeyboardButton("История приёмов пищи", callback_data="m:diary:hist")],
            [InlineKeyboardButton("Рекомендуемые нормы", callback_data="m:diary:norms")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")],
        ]
    )


def kb_profile_section() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Информация", callback_data="m:prof:info")],
            [InlineKeyboardButton("Редактировать цель", callback_data="m:prof:goal")],
            [InlineKeyboardButton("Актуальный вес", callback_data="m:prof:weight")],
            [InlineKeyboardButton("Динамика веса", callback_data="m:prof:chart")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")],
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


def kb_years() -> InlineKeyboardMarkup:
    years = list(range(1990, 2016))
    rows = []
    for i in range(0, len(years), 3):
        chunk = years[i : i + 3]
        rows.append(
            [InlineKeyboardButton(str(y), callback_data=f"m:bd:y:{y}") for y in chunk]
        )
    rows.append([InlineKeyboardButton("⬅ Назад", callback_data="m:onb:back")])
    return InlineKeyboardMarkup(rows)


def kb_months() -> InlineKeyboardMarkup:
    rows = []
    for i in range(1, 13, 3):
        rows.append(
            [
                InlineKeyboardButton(str(m), callback_data=f"m:bd:m:{m:02d}")
                for m in range(i, min(i + 3, 13))
            ]
        )
    rows.append([InlineKeyboardButton("⬅ Год", callback_data="m:onb:bd")])
    return InlineKeyboardMarkup(rows)


def kb_days(year: int, month: int) -> InlineKeyboardMarkup:
    import calendar

    _, ndays = calendar.monthrange(year, month)
    rows = []
    for d in range(1, ndays + 1, 4):
        row = []
        for dd in range(d, min(d + 4, ndays + 1)):
            row.append(InlineKeyboardButton(str(dd), callback_data=f"m:bd:d:{dd}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅ Месяц", callback_data="m:bd:backm")])
    return InlineKeyboardMarkup(rows)


def kb_tariffs() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("1 неделя — 70 ₽", callback_data="m:sub:order:tariff_1w")],
            [InlineKeyboardButton("2 недели — 126 ₽", callback_data="m:sub:order:tariff_2w")],
            [InlineKeyboardButton("1 месяц — 210 ₽", callback_data="m:sub:order:tariff_1m")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="m:main")],
        ]
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
    if pr.get("missing_fields"):
        text += f"\n\n(Профиль можно дополнить: {', '.join(pr['missing_fields'])})"
    sub = _has_active_sub(u.id)
    await update.message.reply_text(text, reply_markup=kb_main(sub_active=sub))


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.data or not update.effective_user:
        return
    await q.answer()
    uid = update.effective_user.id
    data = q.data
    uname = update.effective_user.username
    fname = update.effective_user.first_name

    try:
        await _dispatch_menu(q, uid, uname, fname, data, context)
    except Exception as e:
        logger.exception("menu %s: %s", data, e)
        await context.bot.send_message(chat_id=uid, text="Ошибка запроса к серверу. Попробуй позже.")


async def _dispatch_menu(q, uid: int, uname: str | None, fname: str | None, data: str, context) -> None:
    if data == "m:main":
        USER_STATES.pop(uid, None)
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
        return

    if data == "m:onb:act":
        await q.edit_message_text("Уровень физической активности:", reply_markup=kb_activity())
        return
    if data.startswith("m:set:act:"):
        kfa = data.split(":")[-1]
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "activity_level": kfa})
        await q.edit_message_text("Активность сохранена.", reply_markup=kb_onboarding())
        return

    if data == "m:onb:bd":
        st = USER_STATES.setdefault(uid, {})
        st["bd"] = {}
        await q.edit_message_text("Выберите год рождения (старт с 2000-х годов в сетке ниже):", reply_markup=kb_years())
        return
    if data.startswith("m:bd:y:"):
        y = int(data.split(":")[-1])
        USER_STATES.setdefault(uid, {}).setdefault("bd", {})["y"] = y
        await q.edit_message_text(f"Год {y}. Выберите месяц:", reply_markup=kb_months())
        return
    if data.startswith("m:bd:m:"):
        m = int(data.split(":")[-1])
        st = USER_STATES.setdefault(uid, {})
        st.setdefault("bd", {})["m"] = m
        y = st["bd"].get("y") or 2000
        await q.edit_message_text(f"Дата: {y}-{m:02d}. Выберите день:", reply_markup=kb_days(y, m))
        return
    if data == "m:bd:backm":
        st = USER_STATES.get(uid, {}).get("bd") or {}
        y = st.get("y") or 2000
        await q.edit_message_text(f"Год {y}. Выберите месяц:", reply_markup=kb_months())
        return
    if data.startswith("m:bd:d:"):
        d = int(data.split(":")[-1])
        st = USER_STATES.setdefault(uid, {}).get("bd") or {}
        y, m = st.get("y"), st.get("m")
        if not y or not m:
            await q.edit_message_text("Сначала выберите год и месяц.", reply_markup=kb_onboarding())
            return
        try:
            bd = date(y, m, d)
        except ValueError:
            await q.answer("Некорректная дата", show_alert=True)
            return
        tg_api.patch_json("/users/profile", {"telegram_id": uid, "birth_date": bd.isoformat()})
        USER_STATES.get(uid, {}).pop("bd", None)
        await q.edit_message_text("Дата рождения сохранена.", reply_markup=kb_onboarding())
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
        await q.edit_message_text("Укажите желаемый вес в килограммах (например: 60). Напишите в чат.")
        return

    if data == "m:diary":
        USER_STATES.setdefault(uid, {})["mode"] = UIMode.IDLE
        await q.edit_message_text(
            "Здесь находится твой дневник питания.\n"
            "Добавляй приёмы пищи по фото или описанию, смотри сводку по нутриентам.",
            reply_markup=kb_diary(),
        )
        return
    if data == "m:diary:add":
        USER_STATES.setdefault(uid, {})["mode"] = UIMode.DIARY_ADD_MEAL
        await q.edit_message_text(
            "Отправь фото блюда или опиши текстом. После анализа можно сохранить или отменить приём.",
            reply_markup=kb_back_main(),
        )
        return
    if data == "m:diary:stats":
        png = tg_api.get_bytes("/nutrition/stats/chart", params={"telegram_id": uid, "days": 7})
        await q.message.reply_photo(photo=BytesIO(png), caption="Статистика за 7 дней (ккал и БЖУ).")
        await q.message.reply_text("Дневник:", reply_markup=kb_diary())
        return
    if data == "m:diary:norms":
        info = tg_api.get_json("/nutrition/recommended", params={"telegram_id": uid})
        if info.get("status") != "ok":
            await q.message.reply_text(info.get("message", "Недостаточно данных для расчёта нормы."))
        else:
            await q.message.reply_text(
                f"Рекомендуемая норма (оценка):\n"
                f"Калории: {info['calories_kcal']:.0f} ккал/день\n"
                f"Белки: {info['protein_g']} г\nЖиры: {info['fat_g']} г\nУглеводы: {info['carbs_g']} г\n"
                f"(БЖУ: 20% / 30% / 50% от калорий; КФА={info['activity_multiplier']})"
            )
        await q.message.reply_text("Дневник:", reply_markup=kb_diary())
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
        detail = tg_api.get_json(f"/meals/{mid}", params={"telegram_id": uid})
        lines = [f"Приём #{detail['id']} {detail['meal_datetime']}", f"Источник: {detail.get('source_type')}"]
        kb_rows = []
        for it in detail.get("items") or []:
            lines.append(f"• {it['item_name']}: {it.get('estimated_weight_g')} г")
            label = (it["item_name"][:18] + "…") if len(it["item_name"]) > 18 else it["item_name"]
            kb_rows.append(
                [InlineKeyboardButton(f"Вес: {label}", callback_data=f"m:he:{mid}:{it['id']}")]
            )
        kb_rows.append([InlineKeyboardButton("Удалить приём", callback_data=f"m:hd:{mid}")])
        kb_rows.append([InlineKeyboardButton("К истории", callback_data="m:diary:hist")])
        await q.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows))
        return
    if data.startswith("m:hd:") and not data.startswith("m:hdc:"):
        mid = int(data.split(":")[-1])
        await q.message.reply_text(
            "Удалить этот приём?",
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
            await q.answer("Некорректная команда", show_alert=True)
            return
        mid, iid = int(parts[2]), int(parts[3])
        USER_STATES.setdefault(uid, {})["awaiting_field"] = f"editw:{mid}:{iid}"
        await q.edit_message_text("Введите новый вес порции в граммах (целое число).")
        return

    if data == "m:prof":
        USER_STATES.setdefault(uid, {})["mode"] = UIMode.IDLE
        await q.edit_message_text(
            "В этом разделе можно следить за весом.\n"
            "Контрольное взвешивание проводить минимум раз в неделю.\n"
            "Для чистоты показателей взвешивайтесь утром натощак, после опорожнения кишечника и мочевого пузыря. "
            "Это позволит исключить погрешность, связанную с естественными процессами пищеварения.\n"
            "Например: в понедельник сразу после пробуждения, завершив все утренние гигиенические процедуры, "
            "но до первого стакана воды или завтрака.",
            reply_markup=kb_profile_section(),
        )
        return
    if data == "m:prof:info":
        pr = _profile(uid)["user"] or {}
        sex_ru = {"male": "мужской", "female": "женский"}.get((pr.get("sex") or "").lower(), pr.get("sex") or "—")
        txt = (
            f"Пол: {sex_ru}\n"
            f"Дата рождения: {pr.get('birth_date') or '—'}\n"
            f"Рост: {pr.get('height_cm') or '—'} см\n"
            f"Вес: {pr.get('weight_kg') or '—'} кг\n"
            f"Желаемый вес: {pr.get('target_weight_kg') or '—'} кг\n"
            f"Активность (КФА): {pr.get('activity_level') or '—'}"
        )
        await q.message.reply_text(txt, reply_markup=kb_profile_section())
        await q.message.reply_text("Изменить пол или активность:", reply_markup=kb_sex())
        await q.message.reply_text("Или открой полный список полей профиля:", reply_markup=kb_onboarding())
        return
    if data == "m:prof:goal":
        pr = _profile(uid)["user"] or {}
        await q.message.reply_text(
            f"Текущий желаемый вес: {pr.get('target_weight_kg') or '—'} кг\nНажми «Редактировать».",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Редактировать", callback_data="m:onb:tweight")]]
            ),
        )
        return
    if data == "m:prof:weight":
        pr = _profile(uid)["user"] or {}
        await q.message.reply_text(
            f"Текущий вес в профиле: {pr.get('weight_kg') or '—'} кг",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Коррекция веса", callback_data="m:prof:wfix")],
                    [InlineKeyboardButton("Отменить последнее взвешивание", callback_data="m:prof:wundo")],
                ]
            ),
        )
        return
    if data == "m:prof:wfix":
        USER_STATES.setdefault(uid, {})["awaiting_field"] = "weight_correction"
        await q.edit_message_text("Введите контрольный вес в кг (число).")
        return
    if data == "m:prof:wundo":
        try:
            tg_api.delete("/users/weights/latest", params={"telegram_id": uid})
            await q.edit_message_text("Последнее взвешивание удалено.")
        except Exception:
            await q.edit_message_text("Не удалось удалить (возможно, записей нет).")
        return
    if data == "m:prof:chart":
        for period, title in (("week", "недели"), ("month", "месяца")):
            png = tg_api.get_bytes("/users/weights/chart", params={"telegram_id": uid, "period": period})
            await q.message.reply_photo(photo=BytesIO(png), caption=f"Динамика веса ({title})")
        await q.message.reply_text("Профиль:", reply_markup=kb_profile_section())
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
            reply_markup=kb_back_main(),
        )
        return
    if data.startswith("m:sub:order:"):
        plan = data.split(":")[-1]
        out = tg_api.post_json("/subscriptions/order", {"telegram_id": uid, "plan": plan})
        await q.edit_message_text(
            f"Заявка создана ({plan}). Статус: {out.get('status')}.\n{out.get('message', '')}",
            reply_markup=kb_back_main(),
        )
        return


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
        await update.message.reply_text("Желаемый вес сохранён.", reply_markup=kb_onboarding())
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
        await update.message.reply_text("Вес записан.", reply_markup=kb_profile_section())
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
            "Вес позиции обновлён (нутриенты пересчитаны по CSV, если доступен).",
            reply_markup=kb_diary(),
        )


class AddMealModeFilter(filters.MessageFilter):
    def filter(self, message):
        u = message.from_user
        if not u:
            return False
        st = USER_STATES.get(u.id) or {}
        return st.get("mode") == UIMode.DIARY_ADD_MEAL


add_meal_mode_filter = AddMealModeFilter()


async def photo_outside_diary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Чтобы добавить приём пищи: «Дневник питания» → «Добавить приём пищи», затем отправь фото."
        )


def build_profile_numeric_handler() -> MessageHandler:
    return MessageHandler(awaiting_numeric_filter & filters.TEXT & ~filters.COMMAND, handle_profile_numeric)

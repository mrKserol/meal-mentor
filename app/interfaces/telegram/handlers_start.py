from telegram import Update
from telegram.ext import ContextTypes


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    await update.message.reply_text(
        "Привет! Я Meal Mentor — оценю состав и калорийность еды по фото или по твоему описанию.\n\n"
        "Как это работает:\n"
        "• Отправь фото блюда — я покажу состав, БЖУ (если есть база) и спрошу, записать ли приём в дневник.\n"
        "• Если фото неясное — опиши текстом, что ешь.\n"
        "• Запись в дневник только после твоего «Да» (кнопка или слово).\n\n"
        "Команды:\n"
        "/start — это сообщение\n"
        "/report [дней] — сводка за последние N дней (по умолчанию 7)"
    )

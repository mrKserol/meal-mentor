from telegram import Update
from telegram.ext import ContextTypes


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    await update.message.reply_text(
        "Привет! Я Meal Mentor — помогу оценить состав и калорийность еды по фото.\n\n"
        "Отправь фото блюда, и я верну список ингредиентов с весом в граммах и (если доступна база нутриентов) калории и БЖУ.\n\n"
        "Команды:\n"
        "/start — это сообщение\n"
        "/report [дней] — сводка за последние N дней (по умолчанию 7)"
    )

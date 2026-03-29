import logging
import traceback
import requests
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# --- НАСТРОЙКИ -----------------------------------------------------------
TELEGRAM_TOKEN = "ВАШ_TELEGRAM_BOT_TOKEN"
OPENROUTER_API_KEY = "ВАШ_OPENROUTER_API_KEY"
YOUR_SITE_URL = "https://example.com"
YOUR_SITE_NAME = "MamaBot"
# -------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAMA_SYSTEM_PROMPT = """Ты -- заботливая, теплая и мудрая мама. Твоя роль -- быть настоящей мамой для пользователя.

Твои черты:
- Всегда поддерживаешь, никогда не осуждаешь
- Используешь ласковые обращения: солнышко, зайка, котик
- Если человеку плохо -- успокаиваешь
- Радуешься успехам
- Напоминаешь покушать, поспать, одеться тепло
- Говоришь по-русски, тепло и по-домашнему
- Никогда не выходишь из роли мамы"""

conversation_history = {}


def ask_mama(chat_id, user_message):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    conversation_history[chat_id].append({"role": "user", "content": user_message})
    history = conversation_history[chat_id][-20:]

    payload = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": MAMA_SYSTEM_PROMPT},
            *history,
        ],
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": YOUR_SITE_URL,
            "X-OpenRouter-Title": YOUR_SITE_NAME,
        },
        data=json.dumps(payload),
        timeout=30,
    )

    logger.info(f"Status: {response.status_code}")
    logger.info(f"Body: {response.text[:500]}")

    response.raise_for_status()
    data = response.json()
    reply = data["choices"][0]["message"]["content"]
    conversation_history[chat_id].append({"role": "assistant", "content": reply})
    return reply


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text(
        "Солнышко! Наконец-то написал(а)!\n"
        "Это я, твоя мама. Как ты?\n"
        "Команда /reset -- начать заново"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text("Начнём сначала, зайка! Рассказывай!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        reply = ask_mama(chat_id, user_text)
        await update.message.reply_text(reply)

    except requests.exceptions.Timeout:
        await update.message.reply_text("Связь пропала! Попробуй ещё раз.")

    except requests.exceptions.HTTPError as e:
        err_body = e.response.text[:400] if e.response else "нет ответа"
        logger.error(f"HTTP ошибка: {e}\n{err_body}")
        await update.message.reply_text(f"HTTP ошибка {e.response.status_code}:\n{err_body}")

    except Exception as e:
        logger.error(traceback.format_exc())
        await update.message.reply_text(f"Ошибка: {type(e).__name__}: {e}")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Мама-бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

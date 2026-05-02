import os
import random
import logging
import telebot
from telebot import types
from groq import Groq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN secret is not set.")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY secret is not set.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

AI_MODEL = "llama3-8b-8192"
HISTORY_LIMIT = 10

history: dict[int, list[dict]] = {}
game_number: dict[int, int] = {}
user_style: dict[int, str] = {}

all_users: set[int] = set()
total_messages: int = 0

STYLES = {
    "😎 Дружелюбный": "Ты дружелюбный ассистент. Отвечай на русском языке.",
    "📚 Учитель": "Ты строгий, но понятный учитель. Отвечай на русском языке.",
    "😂 Шутник": "Ты отвечаешь с юмором. Отвечай на русском языке.",
}


def main_markup() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💬 ИИ Чат", "🎮 Игры")
    markup.add("🧠 Сменить стиль", "❌ Очистить память")
    return markup


# ── СТАРТ ─────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start(message):
    all_users.add(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "Привет! Я прокачанный ИИ-бот 🤖\nВыбери режим 👇",
        reply_markup=main_markup(),
    )


@bot.message_handler(commands=["stats"])
def stats(message):
    bot.send_message(
        message.chat.id,
        f"📊 Статистика бота:\n\n"
        f"👤 Пользователей: {len(all_users)}\n"
        f"💬 Сообщений обработано: {total_messages}",
    )


# ── ИГРЫ ──────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🎮 Игры")
def games(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎲 Угадай число", "🔙 Назад")
    bot.send_message(message.chat.id, "Выбери игру:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "🎲 Угадай число")
def guess_start(message):
    num = random.randint(1, 10)
    game_number[message.chat.id] = num
    bot.send_message(message.chat.id, "Я загадал число от 1 до 10. Попробуй угадать!")


@bot.message_handler(func=lambda m: m.text is not None and m.text.isdigit())
def guess_check(message):
    user_id = message.chat.id
    if user_id in game_number:
        if int(message.text) == game_number[user_id]:
            bot.send_message(user_id, "🎉 Угадал!")
            del game_number[user_id]
        else:
            bot.send_message(user_id, "❌ Не угадал, попробуй ещё")


@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def back(message):
    bot.send_message(
        message.chat.id,
        "Главное меню 👇",
        reply_markup=main_markup(),
    )


# ── СТИЛЬ ИИ ──────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🧠 Сменить стиль")
def change_style(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("😎 Дружелюбный", "📚 Учитель", "😂 Шутник")
    bot.send_message(message.chat.id, "Выбери стиль ИИ:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in STYLES)
def set_style(message):
    user_style[message.chat.id] = STYLES[message.text]
    bot.send_message(
        message.chat.id,
        f"Стиль обновлён ✅ — {message.text}",
        reply_markup=main_markup(),
    )


# ── ПАМЯТЬ ────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "❌ Очистить память")
def clear_memory(message):
    history[message.chat.id] = []
    bot.send_message(message.chat.id, "Память очищена 🧹")


# ── ИИ ЧАТ ────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def chat(message):
    global total_messages
    user_id = message.chat.id
    all_users.add(message.from_user.id)
    total_messages += 1
    convo = history.setdefault(user_id, [])
    convo.append({"role": "user", "content": message.text or ""})
    convo[:] = convo[-HISTORY_LIMIT:]

    system_prompt = user_style.get(user_id, "Ты умный ассистент. Отвечай на русском языке.")

    try:
        bot.send_chat_action(user_id, "typing")
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "system", "content": system_prompt}] + convo,
        )
        answer = response.choices[0].message.content or ""
        convo.append({"role": "assistant", "content": answer})
        convo[:] = convo[-HISTORY_LIMIT:]
        bot.send_message(user_id, answer)
    except Exception as exc:
        log.exception("AI request failed")
        bot.send_message(user_id, f"Ошибка: {exc}")


def main():
    log.info("🔥 Прокачанный бот запущен!")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


if __name__ == "__main__":
    main()
    

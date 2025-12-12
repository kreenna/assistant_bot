import asyncio
import logging
import os
from collections import deque
from typing import List, Dict

import openai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

# конфигурация
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

bot = Bot(token=TOKEN)
dp = Dispatcher()

# хранилище истории диалогов (user_id -> список сообщений)
user_history: Dict[int, deque] = {}

MAX_HISTORY = 20  # максимум сообщений в истории


async def get_chat_response(messages: List[dict]) -> str:
    """Получает ответ от ChatGPT с учетом истории."""

    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко и по делу."},
                *messages[-MAX_HISTORY:]
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Извините, произошла ошибка при обращении к ChatGPT."


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start - приветствие и сброс истории."""
    user_id = message.from_user.id
    user_history[user_id] = deque(maxlen=MAX_HISTORY)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новый запрос", callback_data="reset_chat")]
    ])

    await message.answer(
        "Привет! Я бот с ChatGPT. Пиши любой вопрос - отвечу с учетом контекста.\n"
        "🔄 /start, /help - сбросить историю\n"
        "🆕 Кнопка 'Новый запрос' ниже",
        reply_markup=keyboard
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help."""
    await message.answer(
        "📖 Помощь:\n"
        "• Пиши любой текст - получу ответ от ChatGPT\n"
        "• История диалога сохраняется автоматически\n"
        "• /start, /help или кнопка 'Новый запрос' - сброс контекста\n"
    )


@dp.callback_query(F.data == "reset_chat")
async def reset_chat(callback: types.CallbackQuery):
    """Сброс истории по кнопке."""
    user_id = callback.from_user.id
    user_history[user_id] = deque(maxlen=MAX_HISTORY)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новый запрос", callback_data="reset_chat")]
    ])

    await callback.message.edit_text(
        "✅ История сброшена! Теперь новый диалог.\n"
        "Пиши вопрос - отвечу с чистого листа.",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.message(F.text)
async def handle_message(message: types.Message):
    """Обработка текстовых сообщений с сохранением контекста."""
    user_id = message.from_user.id

    # инициализация истории если нет
    if user_id not in user_history:
        user_history[user_id] = deque(maxlen=MAX_HISTORY)

    history = user_history[user_id]

    # добавляем сообщение пользователя
    history.append({"role": "user", "content": message.text})

    # получаем ответ
    response = await get_chat_response(list(history))

    # добавляем ответ бота в историю
    history.append({"role": "assistant", "content": response})

    # показываем кнопку сброса
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новый запрос", callback_data="reset_chat")]
    ])

    await message.answer(response, reply_markup=keyboard)


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

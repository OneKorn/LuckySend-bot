import os
import logging
import random
import json
from decimal import Decimal
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ====== Конфигурация через переменные среды ======
API_TOKEN = os.getenv("BOT_TOKEN")        # Токен вашего бота
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Ваш Telegram ID для админ-команд
DATA_FILE = os.getenv("DATA_FILE", "data.json")  # Файл хранения участников

# Проверка обязательных переменных
if not API_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных среды")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ====== Работа с данными ======
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"participants": [], "total_amount": "0.00"}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ====== Хэндлеры ======
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🤑 Участвовать", callback_data="participate")
    )
    await message.answer(
        "Привет! Я бот для розыгрыша донатов.\n"
        "Нажми кнопку ниже, чтобы внести сумму и участвовать.",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == "participate")
async def participate_cb(callback: types.CallbackQuery):
    await bot.send_message(
        callback.from_user.id,
        "Введите сумму доната в гривнах цифрами (например: 1500):"
    )

@dp.message_handler(lambda m: m.text and m.text.isdigit())
async def manual_donate(message: types.Message):
    amount_uah = int(message.text)
    data = load_data()
    data["participants"].append({"user_id": message.from_user.id, "amount": amount_uah})
    total = Decimal(data.get("total_amount", "0.00")) + Decimal(amount_uah)
    data["total_amount"] = str(total)
    save_data(data)
    await message.reply(f"Спасибо за донат {amount_uah}₴! Сумма всех донатов: {total}₴")

@dp.message_handler(commands=["status"])
async def status_handler(message: types.Message):
    data = load_data()
    total = Decimal(data.get("total_amount", "0.00"))
    participants = len({p['user_id'] for p in data.get("participants", [])})
    await message.reply(f"Всего собрано: {total}₴ от {participants} участников.")

@dp.message_handler(commands=["draw"])
async def draw_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("У вас нет прав для этой команды.")
        return
    data = load_data()
    if not data.get("participants"):  # пустой список
        await message.reply("Нет участников для розыгрыша.")
        return
    winner = random.choice(data["participants"])
    winner_id = winner["user_id"]
    prize = data.get("total_amount", "0.00")
    # Сброс после розыгрыша
    save_data({"participants": [], "total_amount": "0.00"})
    # Оповещение
    await bot.send_message(winner_id, f"🎉 Поздравляем! Вы выиграли {prize}₴! 🎉")
    await message.reply(f"Розыгрыш завершён. Победитель: {winner_id}, приз: {prize}₴")

# ====== Запуск ======
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

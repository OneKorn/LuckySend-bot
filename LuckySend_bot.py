import os
import logging
import random
import json
from decimal import Decimal
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ====== Конфигурация через переменные среды ======
API_TOKEN = os.getenv("BOT_TOKEN")  # Токен твоего бота
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_TOKEN")  # Токен Telegram Payments или другого провайдера
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Айди администратора для команд админа
DATA_FILE = os.getenv("DATA_FILE", "data.json")  # Путь к файлу хранения участников

if not API_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных среды")
# PAYMENT_PROVIDER_TOKEN может быть пустым
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ====== Функции работы с данными ======
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"participants": [], "total_amount": "0.00"}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ====== Хэндлеры бота ======
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🤑 Участвовать", callback_data="participate")
    )
    text = (
        "Привет! Я бот для розыгрыша донатов.\n"
        "Нажми кнопку ниже, чтобы внести донат и автоматически участвовать."
    )
    await message.answer(text, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "participate")
async def participate_cb(callback: types.CallbackQuery):
    if PAYMENT_PROVIDER_TOKEN:
        # старая логика с send_invoice
        prices = [types.LabeledPrice(label="Донат на розыгрыш", amount=5000)]
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Донат на розыгрыш",
            description="Сумма пойдет в общий фонд месячного розыгрыша.",
            payload="donation_payload",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency="UAH",
            prices=prices,
        )
    else:
        await bot.send_message(
            callback.from_user.id,
            "Введите, пожалуйста, сумму доната в гривнах цифрами (например: 1500):"
        )



@dp.pre_checkout_query_handler(lambda q: True)
async def pre_checkout(pre_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_q.id, ok=True)


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def payment_success(message: types.Message):
    data = load_data()
    user_id = message.from_user.id
    amount = message.successful_payment.total_amount  # сумма в копейках
    uah = amount / 100
    # Добавляем участника
    data["participants"].append({"user_id": user_id, "amount": uah})
    total = Decimal(data.get("total_amount", "0.00")) + Decimal(uah)
    data["total_amount"] = str(total)
    save_data(data)
    await message.answer(f"Спасибо за донат {uah:.2f}₴! Ты в розыгрыше.")


@dp.message_handler(lambda m: m.text and m.text.isdigit())
async def manual_donate(message: types.Message):
    uah = int(message.text)
    data = load_data()
    data["participants"].append({"user_id": message.from_user.id, "amount": uah})
    total = Decimal(data.get("total_amount", "0.00")) + Decimal(uah)
    data["total_amount"] = str(total)
    save_data(data)
    await message.answer(f"Спасибо за донат {uah}₴! Ты в розыгрыше.")
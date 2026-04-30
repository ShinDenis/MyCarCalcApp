import os
import asyncio
import logging
from threading import Thread
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, WebAppInfo
)
from google import genai

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Настройки ---
API_TOKEN = os.environ.get("API_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
WEBAPP_URL = f"{RENDER_EXTERNAL_URL}/webapp/"

if not API_TOKEN:
    raise RuntimeError("Переменная окружения API_TOKEN не задана!")
if not GEMINI_API_KEY:
    raise RuntimeError("Переменная окружения GEMINI_API_KEY не задана!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Настройка Gemini ---
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

# --- Логика калькулятора ---
def calc_total(price: float):
    customs = price * 0.15
    logistics = 1000.0
    commission = price * 0.05
    total = price + customs + logistics + commission
    return customs, logistics, commission, total

# --- Inline клавиатуры ---
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚗 Открыть калькулятор",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")],
    ])

# --- Keep-alive ---
async def keep_alive():
    async with httpx.AsyncClient() as http:
        while True:
            await asyncio.sleep(600)
            try:
                await http.get(f"{RENDER_EXTERNAL_URL}/")
                logger.info("Keep-alive ping отправлен")
            except Exception as e:
                logger.warning(f"Keep-alive ошибка: {e}")

# --- Хэндлеры команд ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Вас приветствует <b>Бот калькулятор</b>!\n\n"
        "Рассчитаю полную стоимость авто с учётом таможни, логистики и комиссии.\n\n"
        "Нажмите кнопку ниже чтобы открыть калькулятор:",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "Нажмите <b>Открыть калькулятор</b> — приложение откроется прямо в Telegram.\n\n"
        "Введите модель и цену авто, нажмите <b>Рассчитать</b>.\n\n"
        "<b>Что входит в расчёт:</b>\n"
        "🛃 Таможня — 15% от цены\n"
        "🚚 Логистика — 1000 USD\n"
        "💼 Комиссия — 5% от цены",
        parse_mode="HTML",
        reply_markup=back_kb()
    )

# --- Callback хэндлеры ---
@dp.callback_query(F.data == "start")
async def cb_start(call: CallbackQuery):
    await call.message.edit_text(
        "👋 Вас приветствует <b>Бот калькулятор</b>!\n\n"
        "Рассчитаю полную стоимость авто с учётом таможни, логистики и комиссии.\n\n"
        "Нажмите кнопку ниже чтобы открыть калькулятор:",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )
    await call.answer()

@dp.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "Нажмите <b>Открыть калькулятор</b> — приложение откроется прямо в Telegram.\n\n"
        "Введите модель и цену авто, нажмите <b>Рассчитать</b>.\n\n"
        "<b>Что входит в расчёт:</b>\n"
        "🛃 Таможня — 15% от цены\n"
        "🚚 Логистика — 1000 USD\n"
        "💼 Комиссия — 5% от цены",
        parse_mode="HTML",
        reply_markup=back_kb()
    )
    await call.answer()

# --- Текстовые сообщения (fallback) ---
@dp.message()
async def fallback(message: types.Message):
    await message.answer(
        "Используйте кнопку ниже для открытия калькулятора 👇",
        reply_markup=main_menu_kb()
    )

# --- Установка меню команд ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Справка"),
    ]
    await bot.set_my_commands(commands)

# --- REST API + статика ---
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running"}

@app.get("/calc/{price}")
def api_calc(price: float):
    if price <= 0:
        return {"error": "Цена должна быть положительной"}
    customs, logistics, commission, total = calc_total(price)
    return {
        "price": round(price, 2),
        "customs": round(customs, 2),
        "logistics": round(logistics, 2),
        "commission": round(commission, 2),
        "total": round(total, 2)
    }

# Раздаём папку webapp как статику
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")

def run_api():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# --- Запуск бота ---
async def run_bot():
    await set_commands(bot)
    asyncio.create_task(keep_alive())
    dp.shutdown.register(lambda: bot.session.close())
    await dp.start_polling(bot, drop_pending_updates=True)

def main():
    Thread(target=run_api, daemon=True).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
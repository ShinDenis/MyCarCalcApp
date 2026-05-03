import os
import asyncio
import logging
from threading import Thread
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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

# --- Fallback ---
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

# --- REST API ---
app = FastAPI()

class CalcRequest(BaseModel):
    model: str
    price: float

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

@app.post("/calc-ai")
async def api_calc_ai(req: CalcRequest):
    if req.price <= 0:
        return {"error": "Цена должна быть положительной"}

    customs, logistics, commission, total = calc_total(req.price)

    prompt = (
        f"Пользователь хочет купить автомобиль: {req.model}, итоговая стоимость {total:.2f} USD.\n\n"
        f"Напиши короткий (2-3 предложения) дружелюбный комментарий на русском языке с эмодзи. "
        f"Только эмоции и впечатления об автомобиле. "
        f"Без цифр, без расчётов, без списков — только живой текст."
        f'Если нужна помощь можно связаться со специалистом по ссылке https://t.me/crazymixparty'
    )

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            return {
                "price": round(req.price, 2),
                "customs": round(customs, 2),
                "logistics": round(logistics, 2),
                "commission": round(commission, 2),
                "total": round(total, 2),
                "ai_text": response.text
            }
        except Exception as e:
            error_str = str(e)
            is_503 = "503" in error_str or "UNAVAILABLE" in error_str
            is_429 = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
            if (is_503 or is_429) and attempt < MAX_RETRIES - 1:
                logger.warning(f"Gemini retry {attempt+1}...")
                await asyncio.sleep((attempt + 1) * 5)
                continue
            logger.warning(f"Gemini недоступен: {e}")
            break

    # Fallback без AI
    return {
        "price": round(req.price, 2),
        "customs": round(customs, 2),
        "logistics": round(logistics, 2),
        "commission": round(commission, 2),
        "total": round(total, 2),
        "ai_text": None
    }

# Статика — папка webapp
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
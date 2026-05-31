import os
import asyncio
import logging
import httpx
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, WebAppInfo
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Настройки ---
API_TOKEN = os.environ.get("API_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
WEBAPP_URL = f"{RENDER_EXTERNAL_URL}/webapp/"
SPECIALIST_URL = "https://t.me/crazymixparty"

if not API_TOKEN:
    raise RuntimeError("API_TOKEN не задана!")

# Определяем режим разработки
IS_DEV = RENDER_EXTERNAL_URL.startswith("http://localhost")
IS_HTTPS = WEBAPP_URL and WEBAPP_URL.startswith("https://")

if IS_DEV:
    logger.warning("⚠️  РЕЖИМ РАЗРАБОТКИ - Для Mini App используй ngrok!")
else:
    logger.info("✅ РЕЖИМ ПРОДАКШЕНА - Mini App готово")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# --- Inline клавиатуры ---
def main_menu_kb():
    """Главное меню с проверкой HTTPS"""
    kb = []

    # Веб-приложение (только если HTTPS)
    if IS_HTTPS:
        kb.append([InlineKeyboardButton(
            text="🚗 Открыть калькулятор",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )])
    else:
        # Fallback для локальной разработки
        kb.append([InlineKeyboardButton(
            text="🚗 Открыть в браузере",
            url=f"{RENDER_EXTERNAL_URL}/webapp/"
        )])

    kb.append([InlineKeyboardButton(text="❓ Помощь", callback_data="help")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start")],
    ])


# --- Keep-alive для Render ---
async def keep_alive():
    async with httpx.AsyncClient() as http:
        while True:
            await asyncio.sleep(600)
            try:
                await http.get(f"{RENDER_EXTERNAL_URL}/", timeout=5)
                logger.info("✅ Keep-alive ping отправлен")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive ошибка: {e}")


# --- Команды бота ---
@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info(f"👤 User {message.from_user.id} запустил /start")
    await message.answer(
        "👋 Вас приветствует <b>Бот калькулятор</b>!\n\n"
        "Рассчитаю полную стоимость авто с учётом таможни, логистики и комиссии.\n\n"
        "Нажмите кнопку ниже чтобы открыть калькулятор:",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    logger.info(f"👤 User {message.from_user.id} запросил /help")
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
    logger.info(f"👤 User {call.from_user.id} нажал 'Главное меню'")
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
    logger.info(f"👤 User {call.from_user.id} нажал 'Помощь'")
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
    logger.info(f"👤 User {message.from_user.id} отправил неизвестную команду")
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
    logger.info("✅ Команды бота установлены")


# --- Запуск бота ---
async def main():
    logger.info("🤖 Telegram бот запускается...")
    logger.info(f"📍 URL: {RENDER_EXTERNAL_URL}")
    logger.info(f"🔗 WEBAPP_URL: {WEBAPP_URL or '❌ Не установлена'}")
    await set_commands(bot)
    # asyncio.create_task(keep_alive())

    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
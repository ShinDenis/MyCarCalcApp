import os
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import logging
from google import genai

import bot

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Настройки ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY не задана!")

client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash-lite"

# --- Логика калькулятора ---
def calc_total(price: float):
    customs = price * 0.15
    logistics = 1000.0
    commission = price * 0.05
    total = price + customs + logistics + commission
    return customs, logistics, commission, total

# --- FastAPI приложение ---
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
    logger.info("🤖 Бот запущен внутри FastAPI")

class CalcRequest(BaseModel):
    model: str
    price: float

@app.get("/")
def home():
    return {"status": "API is running"}

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
        f"Без цифр, без расчётов, без списков — только живой текст.\n"
        f"Обязательно предложи помощь специалиста."
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

    return {
        "price": round(req.price, 2),
        "customs": round(customs, 2),
        "logistics": round(logistics, 2),
        "commission": round(commission, 2),
        "total": round(total, 2),
        "ai_text": None
    }

# --- Раздача статичных файлов ---
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")


async def start_bot():
    # вызываем main() из bot.py
    await bot.main()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
# Калькулятор стоимости авто

Telegram бот с Mini App для расчёта полной стоимости автомобиля с учётом таможни, логистики и комиссии.

## Структура проекта

```
├── bot.py                 # Основной код бота и API
├── requirements.txt       # Python зависимости
├── render.yaml           # Конфигурация для Render
├── .env                  # Локальные переменные
├── .gitignore           
└── webapp/
    ├── index.html       # Mini App интерфейс
    └── splash.gif       # Заставка при загрузке
```

Бот будет доступен на:
- **Mini App**: http://localhost:8000/webapp/
- **API**: http://localhost:8000/calc/5000

## Деплой на Render

## Технологический стек

- **Бот**: aiogram 3.27
- **API**: FastAPI
- **AI**: Google Gemini 2.5 Flash
- **Хостинг**: Render (Free план)

## Поддержка

Проблемы? Посмотри логи:
```bash
# Локально
python bot.py

# На Render
Logs → "View logs"
```

## Лицензия

MIT

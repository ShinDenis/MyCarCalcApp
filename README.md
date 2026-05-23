# Калькулятор стоимости авто

Telegram бот с Mini App для расчёта полной стоимости автомобиля с учётом таможни, логистики и комиссии, с подключенной моделью Gemini для живых ответов.

## Структура проекта

```
├── bot.py                 # Бот и API
├── requirements.txt       # Зависимости
├── render.yaml           # Конфигурация для Render
├── .env                  # Локальные переменные
├── .gitignore           
└── webapp/
    ├── index.html       # Front интерфейс
    └── splash.gif       # Заставка
```
## Локальный запуск

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
## Лицензия

MIT

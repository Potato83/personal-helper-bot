# my telegram helper bot

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/aiogram-3.x-blue?logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)

Приватный Telegram-бот ассистент с функциями умных напоминаний, утренней сводки, интеграцией с Google Calendar и мониторингом состояния сети. 

## 🌟 Основные фичи

- **🔒 Приватность:** Бот отвечает только владельцу (реализовано через кастомный Middleware).
- **⏰ Умные напоминания:** Понимание естественного времени (через X минут, завтра в 14:00) с сохранением в SQLite.
- **📅 Google Calendar:** Быстрое добавление событий и просмотр расписания на день напрямую из Telegram.
- **🌅 Утренняя сводка:** Ежедневный автоматический сбор данных (курсы валют, погода OpenWeatherMap, новости RSS, статус серверов).
- **🌐 Network Monitor:** Парсинг Downdetector для отслеживания региональных сбоев интернета с алармами в реальном времени.

## 🛠 Технологический стек
- **Backend:** Python 3.12, aiogram 3.x
- **Асинхронность:** aiohttp, asyncio
- **Фоновые задачи:** APScheduler
- **Парсинг:** BeautifulSoup4 (lxml), dateparser
- **База Данных:** SQLite3
- **Инфраструктура:** Docker, Docker Compose, GitHub Actions (CI/CD)
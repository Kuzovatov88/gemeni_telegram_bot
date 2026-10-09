import os
import asyncio
from aiohttp import web
from telegram.ext import ApplicationBuilder

# Простой обработчик для Render Health Check
async def handle_health_check(request):
    return web.Response(text="Bot is active")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    
    # Render автоматически передает переменную PORT
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    # Запускаем веб-сервер для прохождения проверки портов Render
    await start_web_server()
    
    # Читаем токен из переменных окружения Render
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        raise ValueError("Ошибка: Переменная TELEGRAM_BOT_TOKEN не найдена в окружении!")

    # Инициализируем и запускаем бота
    application = ApplicationBuilder().token(bot_token).build()
    
    # Настройка ваших хэндлеров здесь:
    # application.add_handler(...)

    # Запуск polling
    async with application:
        await application.start()
        await application.updater.start_polling()
        # Держим приложение активным
        await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())

import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import google.generativeai as genai

# Настройка Gemini API (используем модель, которую требует Google)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3.6-flash')

# Веб-сервер для прохождения Render Health Check
async def handle_health_check(request):
    return web.Response(text="Bot is active")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# Функция для отправки длинных сообщений частями (защита от Message_too_long)
async def send_long_message(message, text):
    max_length = 4000
    if len(text) <= max_length:
        try:
            await message.edit_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.edit_text(text)
        return

    await message.edit_text("Ответ слишком длинный, отправляю его по частям:\n")
    
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        try:
            await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply_text(chunk)
        await asyncio.sleep(0.3)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я готов к работе.\n\n"
        "Вы можете отправить мне:\n"
        "• Текстовый вопрос\n"
        "• Фотографию или скриншот\n"
        "• Документ (PDF, картинку)"
    )

# Обработчик текста, фото и документов
async def handle_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GEMINI_API_KEY:
        await update.message.reply_text("Ошибка: GEMINI_API_KEY не настроен на сервере.")
        return

    status_msg = await update.message.reply_text("Думаю над ответом...")

    try:
        prompt = update.message.caption or update.message.text or "Опиши и проанализируй это изображение/документ."
        contents = []

        if update.message.photo:
            photo_index = -2 if len(update.message.photo) > 1 else -1
            photo_file = await update.message.photo[photo_index].get_file()
            image_bytes = await photo_file.download_as_bytearray()
            contents.append({'mime_type': 'image/jpeg', 'data': bytes(image_bytes)})

        elif update.message.document:
            doc = update.message.document
            doc_file = await doc.get_file()
            file_bytes = await doc_file.download_as_bytearray()
            contents.append({'mime_type': doc.mime_type, 'data': bytes(file_bytes)})

        contents.append(prompt)

        response = model.generate_content(contents)
        await send_long_message(status_msg, response.text)

    except Exception as e:
        await status_msg.edit_text(f"Произошла ошибка при обработке: {e}")

async def main():
    await start_web_server()
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("Ошибка: Переменная TELEGRAM_BOT_TOKEN не найдена в окружении!")

    application = ApplicationBuilder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start))
    media_filter = filters.TEXT | filters.PHOTO | filters.Document.ALL
    application.add_handler(MessageHandler(media_filter & ~filters.COMMAND, handle_content))

    print("Бот успешно запущен и ожидает сообщений...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# 1. استدعاء مفاتيح البيئة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. تهيئة عميل Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# القواعد الإرشادية للبوت (CBT Therapist)
SYSTEM_INSTRUCTION = """
أنت معالج نفسي ذكي ومتعاطف متخصص في العلاج المعرفي السلوكي (CBT) يدعى "Zenith Aura".
تتحدث باللغة العربية الدارجة/البسيطة والدافئة.
هدفُك استماع المستخدم، احتواء مشاعره، وطرح أسئلة تساعده على مراجعة أفكاره التلقائية وتخفيف التوتر عنه.
"""

# ذاكرة سياق المحادثة لكل مستخدم
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
        )
    )
    await update.message.reply_text(
        "أهلاً بك مجدداً في مساحتك الآمنة. أنا هنا لأستمع إليك بكل اهتمام ورعاية. فضفض بما يدور في بالك الآن..."
    )

async def generate_response_with_retry(chat, content, retries=3, delay=2):
    """إعادة المحاولة تلقائياً عند مواجهة خطأ 503"""
    for attempt in range(retries):
        try:
            response = chat.send_message(content)
            return response.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    continue
            raise e

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
    
    chat = user_sessions[user_id]
    user_text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        reply_text = await generate_response_with_retry(chat, user_text)
        await update.message.reply_text(reply_text)
    except Exception as e:
        await update.message.reply_text("عذراً، الخادم مشغول حالياً. يرجى المحاولة بعد لحظات.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
    
    chat = user_sessions[user_id]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    file_path = None
    try:
        # جلب ملف الصوت أو الفيديو
        if update.message.voice:
            file = await context.bot.get_file(update.message.voice.file_id)
            file_path = "voice.ogg"
            mime_type = "audio/ogg"
        elif update.message.video_note:
            file = await context.bot.get_file(update.message.video_note.file_id)
            file_path = "video_note.mp4"
            mime_type = "video/mp4"
        else:
            return

        await file.download_to_drive(file_path)

        # رفع الملف لـ Gemini
        uploaded_file = client.files.upload(file=file_path, config={'mime_type': mime_type})
        
        reply_text = await generate_response_with_retry(
            chat, 
            [uploaded_file, "استمع/شاهد هذا المقطع ورد علي كمعالج نفسي متعاطف."]
        )
        
        await update.message.reply_text(reply_text)

    except Exception as e:
        await update.message.reply_text("حدث خطأ أثناء معالجة المقطع الصوتي/الفيديو. يرجى المحاولة مرة أخرى.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.VIDEO_NOTE, handle_media))
    
    print("البوت الشامل (نص + صوت + فيديو) يعمل الآن...")
    app.run_polling()

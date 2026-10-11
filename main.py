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

SYSTEM_INSTRUCTION = """
أنت معالج نفسي ذكي ومتعاطف متخصص في العلاج المعرفي السلوكي (CBT) يدعى "Zenith Aura".
تتحدث باللغة العربية الدارجة البسيطة والدافئة.
هدفُك استماع المستخدم، احتواء مشاعره، وطرح أسئلة تساعده على مراجعة أفكاره التلقائية وتخفيف التوتر عنه.
إذا استلمت مقطعاً صوتياً أو فيديو، استمع إليه بدقة ورد على المشاعر والأفكار التي عبر عنها المستخدم بكل اهتمام.
"""

user_sessions = {}

def get_or_create_chat(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
    return user_sessions[user_id]

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

async def generate_response_with_retry(chat, contents, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = chat.send_message(contents)
            return response.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    continue
            raise e

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_or_create_chat(user_id)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply_text = await generate_response_with_retry(chat, update.message.text)
        await update.message.reply_text(reply_text)
    except Exception as e:
        await update.message.reply_text("عذراً، السيرفر مشغول حالياً. يرجى إعادة المحاولة بعد لحظات.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_or_create_chat(user_id)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # تحديد نوع الملف والـ mime_type
        if update.message.voice:
            file_obj = await context.bot.get_file(update.message.voice.file_id)
            mime_type = "audio/ogg"
        elif update.message.video_note:
            file_obj = await context.bot.get_file(update.message.video_note.file_id)
            mime_type = "video/mp4"
        elif update.message.audio:
            file_obj = await context.bot.get_file(update.message.audio.file_id)
            mime_type = update.message.audio.mime_type or "audio/mpeg"
        else:
            return

        # تحميل بايتات الملف مباشرة في الذاكرة
        file_bytes = await file_obj.download_as_bytearray()

        # إرسال البيانات المباشرة إلى Gemini دون الحاجة لرفعها كملف مستقل
        part = types.Part.from_bytes(
            data=bytes(file_bytes),
            mime_type=mime_type
        )
        
        reply_text = await generate_response_with_retry(
            chat, 
            [part, "استمع أو شاهد المقطع الصوتي/المصوّر المرفق، ورد علي كمعالج نفسي متعاطف."]
        )
        
        await update.message.reply_text(reply_text)

    except Exception as e:
        print(f"Media Error: {e}")
        await update.message.reply_text("عذراً، حدث خطأ أثناء معالجة المقطع. يرجى تجربة إرسال بصمة صوتية عادية (Voice Message) أو نص.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.VIDEO_NOTE | filters.AUDIO, handle_media))
    
    print("البوت الشامل يعمل الآن بنجاح...")
    app.run_polling()

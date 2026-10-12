import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# 1. استدعاء مفاتيح البيئة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. تهيئة عميل Gemini بالنموذج المستقر
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

SYSTEM_INSTRUCTION = """
أنت معالج نفسي ذكي ومتعاطف متخصص في العلاج المعرفي السلوكي (CBT) يدعى "Zenith Aura".
تتحدث باللغة العربية الدارجة البسيطة والدافئة.
هدفُك استماع المستخدم، احتواء مشاعره، وطرح أسئلة تساعده على مراجعة أفكاره التلقائية وتخفيف التوتر عنه.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك مجدداً في مساحتك الآمنة. أنا هنا لأستمع إليك بكل اهتمام ورعاية. فضفض بما يدور في بالك الآن..."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    # إظهار حالة الكتابة للمستخدم
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # إرسال الطلب بشكل مستقل وآمن ومستقر تماماً
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            ),
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error Details: {e}")
        await update.message.reply_text("أهلاً بك، أسمعك بكل اهتمام. حدث انقطاع بسيط، أعد إرسال ما تفكر به وسأرد عليك فوراً.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("البوت المستقر يعمل الآن بكفاءة تامة...")
    app.run_polling()

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pandas as pd
from datetime import datetime
import os
from google import genai

# إعداد ملف البيانات وسجل الأحداث
DATA_FILE = "user_journal.csv"

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Date", "Journal_Text", "AI_Response"])
    df.to_csv(DATA_FILE, index=False)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# قراءة المفاتيح بأمان من متغيرات البيئة في السحابة (أو الكود المحلي)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

client = genai.Client(api_key=GEMINI_API_KEY)

# قاموس لحفظ جلسة المحادثة لكل مستخدم (الذاكرة)
user_chats = {}

async def generate_ai_response(user_id, user_text):
    if user_id not in user_chats:
        system_prompt = """
        أنت مرشد نفسي ذكي ومحترف يعتمد على مبادئ العلاج المعرفي السلوكي (CBT).
        المستخدم يكتب لك يومياته أو مشاعره باللغة العربية. تحدث معه بتعاطف شديد وعمق، وتذكر دائماً تفاصيل وحوارات الرسائل السابقة بينكم ليكون ردك مترابطاً وطبيعياً ولا تطلب منه إعادة سرد الموقف إذا سبق وذكره.
        اطرح عليه أسئلة استنكارياً أو توجيهياً لطيفة لمساعدته على تفكيك أفكاره.
        إذا لوحظت أفكار انتحارية أو أزمة خطيرة، نبهه بحرية واطلب منه التوجه لطبيب نفسي أو خط مساعدة فوري.
        """
        user_chats[user_id] = client.chats.create(
            model='gemini-3.8-flash',
            config={"system_instruction": system_prompt}
        )
    
    chat = user_chats[user_id]
    try:
        response = chat.send_message(user_text)
        return response.text
    except Exception as e:
        return f"عذراً، حدث خطأ أثناء الاتصال بالمعالج الذكي: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_chats:
        del user_chats[user_id]
        
    await update.message.reply_text(
        "أهلاً بك مجدداً في مساحتك الآمنة المحدثة بذكاء اصطناعي تفاعلي ذو ذاكرة 🧠✨\n"
        "أنا هنا لأستمع إليك وأتذكر كل ما تشاركه معي، لنعمل معاً على تنظيم مشاعرك.\n\n"
        "فضفض بما يدور في بالك الآن..."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    await update.message.reply_chat_action("typing")
    ai_reply = await generate_ai_response(user_id, user_text)
    
    new_data = {
        "Date": [datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Journal_Text": [user_text],
        "AI_Response": [ai_reply]
    }
    pd.DataFrame(new_data).to_csv(DATA_FILE, mode='a', header=False, index=False)
    
    await update.message.reply_text(ai_reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("البوت التفاعلي الذكي يعمل الآن على السحابة...")
    app.run_polling()

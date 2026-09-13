import os
import sys
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from ai_parser import parse_user_request
import main as pipeline

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("عذراً، هذا البوت خاص.")
        return

    user_text = update.message.text
    status_msg = await update.message.reply_text("جاري فهم وتفسير طلبك بالذكاء الاصطناعي... ⏳")

    try:
        data = parse_user_request(user_text)
        surah_num = data["surah"]
        start_ayah = data["start_ayah"]
        end_ayah = data["end_ayah"]
        reciter = data["reciter"]
        reciter_name = data["reciter_name"]
        surah_name = data["surah_name"]

        await status_msg.edit_text(
            f"تم استيعاب الطلب! 🎯\n\n"
            f"📖 سورة: {surah_name}\n"
            f"🔢 الآيات: من {start_ayah} إلى {end_ayah}\n"
            f"🎙 القارئ: {reciter_name}\n\n"
            f"جاري تحميل التلاوة ومونتاج الفيديو السينمائي... 🎬"
        )

        v_text, s_name, a_range, r_name, is_fri = pipeline.get_custom_ayahs_data(
            surah_num, start_ayah, end_ayah, reciter, reciter_name
        )

        pipeline.download_aesthetic_background()
        pipeline.build_aesthetic_quran_video(v_text)

        await status_msg.edit_text("تم مونتاج الفيديو! جاري رفعه ونشره إلى حسابك... 🚀")

        public_url = pipeline.upload_video_to_github_release()
        pipeline.post_to_tiktok_via_buffer(public_url, s_name, a_range, r_name, is_fri)

        await update.message.reply_text(
            f"تم النشر بنجاح على حسابك! ✨\n\n🔗 رابط معاينة الفيديو:\n{public_url}"
        )

    except Exception as e:
        print("Error:", e)
        await update.message.reply_text(f"⚠️ خطأ أثناء المعالجة:\n`{str(e)}`", parse_mode="Markdown")

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Missing variables!")
        sys.exit(1)

    print("بوت التليجرام يعمل الآن...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

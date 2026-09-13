import os
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from ai_parser import parse_user_request
import main as pipeline

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التحقق من أن المرسل هو أنت فقط
    if str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("عذراً، هذا البوت خاص وغير مصرح لك باستخدامه.")
        return

    user_text = update.message.text
    status_msg = await update.message.reply_text("جاري فهم طلبك عبر الذكاء الاصطناعي... ⏳")

    try:
        # 1. تحليل الطلب عبر Groq
        data = parse_user_request(user_text)
        surah_num = data["surah"]
        start_ayah = data["start_ayah"]
        end_ayah = data["end_ayah"]
        reciter = data["reciter"]
        reciter_name = data["reciter_name"]
        surah_name = data["surah_name"]

        await status_msg.edit_text(
            f"تم استيعاب الطلب! 🎯\n"
            f"📖 سورة: {surah_name}\n"
            f"🔢 الآيات: من {start_ayah} إلى {end_ayah}\n"
            f"🎙 القارئ: {reciter_name}\n\n"
            f"جاري تحميل التلاوة وتوليد الفيديو السينمائي... 🎬"
        )

        # 2. جلب النصوص والصوتيات المحددة
        v_text, s_name, a_range, r_name, is_fri = pipeline.get_custom_ayahs_data(
            surah_num, start_ayah, end_ayah, reciter, reciter_name
        )

        # 3. بناء وتصدير الفيديو
        pipeline.download_aesthetic_background()
        pipeline.build_aesthetic_quran_video(v_text)

        await status_msg.edit_text("تم توليد الفيديو بنجاح! جاري رفعه وجدولته على تيك توك... 🚀")

        # 4. الرفع والنشر
        public_url = pipeline.upload_video_to_github_release()
        pipeline.post_to_tiktok_via_buffer(public_url, s_name, a_range, r_name, is_fri)

        await update.message.reply_text(
            f"تم نشر الفيديو بنجاح على حسابك! ✨\nرابط الفيديو للمعاينة:\n{public_url}"
        )

    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء التنفيذ: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Telegram Bot is running and waiting for requests...")
    app.run_polling()

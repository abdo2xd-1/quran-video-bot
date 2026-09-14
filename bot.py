import os
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from ai_parser import parse_user_request
import main as pipeline

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().replace("\r", "").replace("\n", "").replace(" ", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip().replace("\r", "").replace("\n", "").replace(" ", "")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = str(update.effective_chat.id).strip()
    user_text = update.message.text.strip()
    print(f"طلب يدوي من ID: {sender_id} | {user_text}", flush=True)

    if sender_id != ADMIN_CHAT_ID:
        await update.message.reply_text("عذراً، هذا البوت خاص بالمسؤول فقط.")
        return

    status_msg = await update.message.reply_text("جاري استيعاب الطلب بالذكاء الاصطناعي... ⏳")

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
            f"جاري المونتاج والتجهيز فوراً... 🎬"
        )

        v_text, s_name, a_range, r_name, is_fri = pipeline.get_custom_ayahs_data(
            surah_num, start_ayah, end_ayah, reciter, reciter_name
        )

        pipeline.download_aesthetic_background()
        pipeline.build_aesthetic_quran_video(v_text)

        await status_msg.edit_text("تم اكتمال المونتاج! جاري الرفع والنشر... 🚀")

        public_url = pipeline.upload_video_to_github_release()

        # إرسال الفيديو للمحادثة
        if os.path.exists("final_reel.mp4"):
            try:
                await update.message.reply_text("جاري إرسال نسخة الفيديو لك هنا... 📥")
                with open("final_reel.mp4", "rb") as video_file:
                    await context.bot.send_video(
                        chat_id=sender_id,
                        video=video_file,
                        caption=f"🎬 سورة {surah_name} ({start_ayah}-{end_ayah})\n🎙 بصوت: {reciter_name}\n\n🔗 الرابط المباشر:\n{public_url}"
                    )
            except Exception as vid_err:
                print(f"Telegram Video sending failed: {vid_err}", flush=True)

        pipeline.post_to_tiktok_via_buffer(public_url, s_name, a_range, r_name, is_fri)

        await update.message.reply_text("✅ تم النشر بنجاح على TikTok و Instagram و YouTube!")

    except Exception as e:
        print(f"Error occurred: {e}", flush=True)
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء المعالجة:\n`{str(e)}`", parse_mode="Markdown")

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("خطأ: تأكد من ضبط إعدادات TELEGRAM_BOT_TOKEN و ADMIN_CHAT_ID!", flush=True)
        sys.exit(1)

    print("بوت التليجرام يعمل الآن ومستعد لتلقي الرسائل 24/7...", flush=True)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(drop_pending_updates=True)

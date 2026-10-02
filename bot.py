import os
import sys
import json
import time
import base64
import random
import shutil
import asyncio
import subprocess
import requests

# ترقيع توافق Pillow مع MoviePy
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None).LANCZOS if hasattr(PIL.Image, 'Resampling') else None)

from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

# سيرفرات التلاوة الكاملة المباشرة بدون تقطيع (MP3Quran CDN)
FULL_SURAHS_SERVERS = {
    "dossari": "https://server11.mp3quran.net/yasser/{:03d}.mp3",
    "alafasy": "https://server8.mp3quran.net/afs/{:03d}.mp3",
    "qatami": "https://server6.mp3quran.net/qtm/{:03d}.mp3",
    "minshawi": "https://server10.mp3quran.net/minsh/{:03d}.mp3"
}

RECITERS_NAMES = {
    "dossari": ("Yasser_Ad-Dussary_128kbps", "ياسر الدوسري"),
    "alafasy": ("Alafasy_128kbps", "مشاري العفاسي"),
    "qatami": ("Nasser_Alqatami_128kbps", "ناصر القطامي"),
    "minshawi": ("Minshawy_Murattal_128kbps", "محمد صديق المنشاوي")
}

def get_font_base64():
    font_path = "Amiri-Bold.ttf"
    if not os.path.exists(font_path) or os.path.getsize(font_path) < 40000:
        try:
            r = requests.get(FONT_URL, timeout=20)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except Exception:
            pass
    if os.path.exists(font_path):
        with open(font_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    return ""

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

# ----------------- 1. محرك فهم النوايا (Gemini AI + Local Safety) -----------------
def analyze_user_intent(user_text):
    text_lower = user_text.lower()
    is_full_explicit = any(k in text_lower for k in ["كامل", "كامله", "كاملة", "طامل", "طامله", "طاملة"])
    
    if "الكهف" in text_lower:
        if is_full_explicit or "شورت" not in text_lower:
            return {"action": "quran_full", "surah_name": "الكهف", "surah_number": 18, "reciter": "dossari"}
        else:
            return {"action": "quran_shorts", "surah_name": "الكهف", "surah_number": 18, "start": 1, "end": 10, "reciter": "dossari"}

    if "الملك" in text_lower:
        return {"action": "quran_full" if is_full_explicit else "quran_shorts", "surah_name": "الملك", "surah_number": 67, "start": 1, "end": 5, "reciter": "dossari"}

    if "الشرح" in text_lower:
        return {"action": "quran_shorts", "surah_name": "الشرح", "surah_number": 94, "start": 1, "end": 8, "reciter": "dossari"}

    if not GEMINI_KEY:
        return {"action": "chat", "reply": "أهلاً بك! يرجى إضافة GEMINI_API_KEY في إعدادات GitHub Secrets."}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    prompt = (
        "أنت Gemini AI، مساعد ذكي وصانع محتوى.\n"
        "افحص رسالة المستخدم:\n"
        "- إذا طلب سورة قرآنية: أرجع JSON يوضح هل هي كاملة أم شورتس.\n"
        "- إذا طلب فيديو عام (فضاء، علم، تحفيز): أرجع action='general_video' مع عنوان وسيناريو 3 جمل.\n"
        "- إذا كان كلاماً عاماً أو سؤالاً: أرجع action='chat' مع ردك المفصل واللطيف.\n\n"
        f"رسالة المستخدم: {user_text}\n"
        "أجب حصراً بصيغة JSON:\n"
        "{\"action\": \"quran_full\"|\"quran_shorts\"|\"general_video\"|\"chat\", \"reply\": \"...\", \"surah_name\": \"...\", \"surah_number\": 18, \"title\": \"...\"}"
    )

    try:
        res = requests.post(
            url, 
            json={"contents": [{"parts": [{"text": prompt}]}]}, 
            params={"key": GEMINI_KEY},
            headers={"Content-Type": "application/json"},
            timeout=15
        ).json()
        parsed = json.loads(res["candidates"][0]["content"]["parts"][0]["text"])
        return parsed
    except Exception:
        return {"action": "chat", "reply": "أهلاً بك يا غالي! أرسل لي اسم السورة التي تريدها أو فكرة الفيديو 🤍"}

# ----------------- 2. تجهيز السورة كاملة والغلاف المعتمد -----------------
def generate_full_surah(surah_num, surah_name, reciter_key, tag):
    rec_key = reciter_key if reciter_key in FULL_SURAHS_SERVERS else "dossari"
    rec_name = RECITERS_NAMES.get(rec_key, ("Dussary", "ياسر الدوسري"))[1]
    
    aud_url = FULL_SURAHS_SERVERS[rec_key].format(surah_num)
    aud_path = f"full_{surah_num}_{tag}.mp3"
    
    # تنزيل ملف التلاوة الكاملة
    r = requests.get(aud_url, timeout=90)
    with open(aud_path, "wb") as f:
        f.write(r.content)

    # تصميم الغلاف المعتمد بدقة 1080x1920
    cover_path = f"cover_full_{tag}.jpg"
    font_b64 = get_font_base64()
    chrome_bin = get_chrome()
    
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; margin: 0; }}
  .box {{ width: 1080px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
  .circle {{ position: absolute; width: 780px; height: 780px; border-radius: 50%; border: 2px solid rgba(212, 175, 55, 0.45); }}
  .badge {{ font-family: 'Amiri'; font-size: 28px; color: #fff; background: rgba(0,0,0,0.5); padding: 8px 24px; border-radius: 20px; margin-bottom: 20px; }}
  .title {{ font-family: 'Amiri'; font-size: 85px; font-weight: bold; color: #D4AF37; margin-bottom: 15px; }}
  .reciter {{ font-family: 'Amiri'; font-size: 40px; color: #fff; }}
</style></head>
<body><div class="box"><div class="circle"></div><div class="badge">🕌 تلاوة خاشعة كاملة 🌿</div><div class="title">سُورَةُ {surah_name} كَامِلَةً</div><div class="reciter">بصوت القارئ {rec_name}</div></div></body></html>"""

    with open("tmp_full_cov.html", "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", f"--screenshot={os.path.abspath(cover_path)}", f"file://{os.path.abspath('tmp_full_cov.html')}"], check=True)

    return aud_path, cover_path, rec_name

# ----------------- 3. معالج رسائل تليجرام -----------------
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    tag = f"{update.effective_user.id}_{int(time.time())}"

    decision = await asyncio.to_thread(analyze_user_intent, user_text)
    action = decision.get("action", "chat")

    if action == "quran_full":
        s_name = decision.get("surah_name", "الكهف")
        s_num = decision.get("surah_number", 18)
        reciter = decision.get("reciter", "dossari")

        status_msg = await update.message.reply_text(
            f"🕌 <b>أمر مؤكد:</b> جاري جلب <b>سورة {s_name} كاملة</b> بصوت القارئ مع الغلاف الرسمي...\n"
            f"⏳ انتظر ثوانٍ معدودة...",
            parse_mode="HTML"
        )
        try:
            aud_file, cov_file, r_name = await asyncio.to_thread(
                generate_full_surah, s_num, s_name, reciter, tag
            )
            with open(aud_file, "rb") as af, open(cov_file, "rb") as cf:
                caption = (
                    f"🕌 <b>سورة {s_name} كاملة</b>\n"
                    f"🎙️ بصوت القارئ: {r_name}\n\n"
                    f"✨ تلاوة نقية كاملة تريح القلب • نور ما بين الجمعتين 🌿"
                )
                await update.message.reply_audio(
                    audio=af,
                    thumbnail=cf,
                    title=f"سورة {s_name} كاملة",
                    performer=r_name,
                    caption=caption,
                    parse_mode="HTML",
                    read_timeout=180,
                    write_timeout=180
                )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ حدث خطأ أثناء التنزيل: {e}")

    elif action == "quran_shorts":
        s_name = decision.get("surah_name", "الكهف")
        await update.message.reply_text(f"🎬 جاري إنتاج مقطع شورتس لسورة {s_name} بالتظليل الذهبي...")

    elif action == "general_video":
        title = decision.get("title", "فيديو اليوم")
        await update.message.reply_text(f"🚀 جاري إنتاج فيديو بالذكاء الاصطناعي بعنوان: <b>{title}</b>...", parse_mode="HTML")

    else:
        reply_text = decision.get("reply", "أهلاً بك! كيف يمكنني مساعدتك اليوم؟ 🤍")
        await update.message.reply_text(reply_text)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"أهلاً بك يا {update.effective_user.first_name} في <b>بوت الذكاء الاصطناعي الشامل</b> 🤖\n\n"
        "أوامر سريعة جاهزة:\n"
        "• اكتب: <code>نزلي سورة الكهف كاملة</code> ➔ تصلك السورة كاملة فوراً مع الغلاف الرسمي 🤍\n"
        "• اكتب: <code>شورتس سورة الكهف</code> ➔ ينتج مقطع ريلز مخصص للنشر.\n"
        "• اسألني أي سؤال أو اطلب أي فيديو وسأنفذه لك مباشرة!"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

def main():
    if not BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN مفقود!", flush=True)
        sys.exit(1)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(180)
        .write_timeout(180)
        .connect_timeout(60)
        .build()
    )
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))

    print("🚀 تم تشغيل البوت الذكي بنجاح 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

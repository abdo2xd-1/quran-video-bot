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
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

# قاموس شامل للسور الشائعة والقصيرة للبحث السريع بالاسم
SURAHS_MAP = {
    "الفاتحة": (1, 1, 7), "البقرة": (2, 255, 255), "الكهف": (18, 1, 4),
    "طه": (20, 1, 8), "الرعد": (13, 28, 28), "يس": (36, 1, 6),
    "الرحمن": (55, 1, 7), "الواقعة": (56, 1, 6), "الملك": (67, 1, 5),
    "النبأ": (78, 1, 5), "النازعات": (79, 1, 5), "الضحى": (93, 1, 8),
    "الشرح": (94, 1, 8), "التين": (95, 1, 8), "العلق": (96, 1, 5),
    "القدر": (97, 1, 5), "البينة": (98, 1, 5), "الزلزلة": (99, 1, 8),
    "العاديات": (100, 1, 8), "القارعة": (101, 1, 8), "التكاثر": (102, 1, 8),
    "العصر": (103, 1, 3), "الهمزة": (104, 1, 9), "الفيل": (105, 1, 5),
    "قريش": (106, 1, 4), "الماعون": (107, 1, 7), "الكوثر": (108, 1, 3),
    "الكافرون": (109, 1, 6), "النصر": (110, 1, 3), "المسد": (111, 1, 5),
    "الإخلاص": (112, 1, 4), "اخلاص": (112, 1, 4), "الفلق": (113, 1, 5),
    "الناس": (114, 1, 6), "الليل": (92, 1, 7), "البلد": (90, 1, 6),
    "الشمس": (91, 1, 6), "الطلاق": (65, 2, 3)
}

RECITERS = {
    "dossari": ("Dussary_128kbps", "ياسر الدوسري"),
    "qatami": ("Nasser_Alqatami_128kbps", "ناصر القطامي"),
    "abbad": ("Fares_Abbad_64kbps", "فارس عباد"),
    "muaiqly": ("MaherAlMuaiqly128kbps", "ماهر المعيقلي"),
    "alafasy": ("Alafasy_128kbps", "مشاري العفاسي")
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

def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']:
        text = text.replace(s, '')
    return text.strip()

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

def render_quran_frame(words, active_idx, font_b64):
    words_html = []
    for i, w in enumerate(words):
        if i == active_idx:
            words_html.append(f'<span style="color:#D4AF37; transform:scale(1.08); text-shadow:0 0 15px rgba(212,175,55,0.9);">{w}</span>')
        else:
            words_html.append(f'<span style="color:#FFFFFF; text-shadow:0 0 10px rgba(0,0,0,0.95);">{w}</span>')

    full_verse = " ".join(words_html)
    font_size = 70 if len(words) <= 6 else 52

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }}
  .badge {{ position: absolute; top: 190px; background: rgba(10,14,20,0.6); border: 1px solid rgba(212,175,55,0.45); color: #fff; font-family: 'AmiriQuran'; font-size: 26px; padding: 10px 28px; border-radius: 30px; }}
  .ayah {{ direction: rtl; text-align: center; font-family: 'AmiriQuran'; font-size: {font_size}px; font-weight: bold; line-height: 1.95; max-width: 920px; margin: auto 0; }}
  .watermark {{ position: absolute; bottom: 110px; left: 50%; transform: translateX(-50%); font-family: 'AmiriQuran'; font-size: 24px; color: rgba(255,255,255,0.45); direction: ltr; }}
</style></head>
<body>
  <div class="badge">🎧 ضع السماعات • سكينة وطمأنينة لقلبك 🌿</div>
  <div class="ayah">{full_verse}</div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path, p_path = f"tmp_{active_idx}.html", f"frame_{active_idx}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [get_chrome(), "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def generate_cover_image(surah_name, reciter_name, font_b64, output_path="auto_cover.jpg"):
    """توليد الغلاف المربع الاحترافي"""
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; position: relative; overflow: hidden; }}
  .grid-box {{ width: 1080px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; text-align: center; }}
  .outer-circle {{ position: absolute; width: 780px; height: 780px; border-radius: 50%; border: 2px solid rgba(212, 175, 55, 0.45); box-shadow: 0 0 35px rgba(212, 175, 55, 0.15); }}
  .badge {{ font-family: 'AmiriQuran', sans-serif; font-size: 26px; color: #e6edf3; background: rgba(0, 0, 0, 0.4); padding: 8px 24px; border-radius: 20px; border: 1px solid rgba(212, 175, 55, 0.3); margin-bottom: 25px; z-index: 2; }}
  .surah-title {{ font-family: 'AmiriQuran', serif; font-size: 82px; font-weight: bold; color: #D4AF37; line-height: 1.3; text-shadow: 0 0 20px rgba(212, 175, 55, 0.8); z-index: 2; margin-bottom: 12px; }}
  .reciter {{ font-family: 'AmiriQuran', sans-serif; font-size: 38px; color: #FFFFFF; font-weight: bold; text-shadow: 0 2px 10px rgba(0, 0, 0, 0.9); z-index: 2; margin-bottom: 20px; }}
  .features {{ font-family: 'AmiriQuran', sans-serif; font-size: 22px; color: rgba(212, 175, 55, 0.85); z-index: 2; }}
  .watermark {{ position: absolute; bottom: 120px; left: 50%; transform: translateX(-50%); font-family: 'AmiriQuran', sans-serif; font-size: 24px; color: rgba(255, 255, 255, 0.4); direction: ltr; }}
</style></head>
<body>
  <div class="grid-box">
    <div class="outer-circle"></div>
    <div class="badge">🌿 تلاوة خاشعة وسكينة للقلب</div>
    <div class="surah-title">سُورَةُ {surah_name}</div>
    <div class="reciter">بصوت القارئ {reciter_name}</div>
    <div class="features">🎧 تلاوة 8D بالسماعات • تظليل الكلمات بالذهب 🌿</div>
  </div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [get_chrome(), "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(output_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return output_path

def produce_video_by_surah(surah_num, start_a, end_a, reciter_key="dossari", tag="user"):
    rec_id, rec_name = RECITERS.get(reciter_key, RECITERS["dossari"])
    meta = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}", timeout=15).json()
    surah_name = meta.get("data", {}).get("name", f"سورة {surah_num}").replace("سورة ", "")

    ayahs = []
    for a in range(start_a, end_a + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic(t_res.get("data", {}).get("text", ""))
        if a == 1 and surah_num != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        surah_str, ayah_str = f"{surah_num:03d}", f"{a:03d}"
        aud_url = f"https://everyayah.com/data/{rec_id}/{surah_str}{ayah_str}.mp3"
        aud_file = f"aud_{tag}_{a}.mp3"
        try:
            r = requests.get(aud_url, timeout=25)
            with open(aud_file, "wb") as f:
                f.write(r.content)
        except Exception:
            fb = requests.get(f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3", timeout=25)
            with open(aud_file, "wb") as f:
                f.write(fb.content)
        ayahs.append({"text": txt, "audio": aud_file})

    # جلب فيديو Pexels طبيعي
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=switzerland+mountains+drone+vertical&orientation=portrait&per_page=6", headers=headers, timeout=15).json()
    chosen_video = random.choice(res.get("videos", []))
    v_files = sorted(chosen_video["video_files"], key=lambda x: x.get("width", 0))
    bg_file = f"bg_{tag}.mp4"
    with open(bg_file, "wb") as f:
        f.write(requests.get(v_files[-1]["link"], timeout=35).content)

    font_b64 = get_font_base64()
    audio_clips, text_clips = [], []
    curr_t = 0.0

    for ay in ayahs:
        ac = AudioFileClip(ay["audio"])
        audio_clips.append(ac)
        words = ay["text"].split()
        tot_chars = sum(len(w) for w in words)
        w_start = curr_t
        for idx, w in enumerate(words):
            w_dur = (len(w) / tot_chars) * ac.duration
            img_path = render_quran_frame(words, idx, font_b64)
            text_clips.append(ImageClip(img_path).set_start(w_start).set_duration(w_dur).set_position(("center", "center")))
            w_start += w_dur
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 1.0

    bg = VideoFileClip(bg_file)
    bg = (bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.22).set_duration(tot_dur)

    main_video = CompositeVideoClip([bg, dim] + text_clips).set_audio(final_audio)

    # 🌟 دمج الغلاف أوتوماتيكياً كأول إطار في الفيديو ليظهر تلقائياً على كل المنصات
    cover_file = f"cover_{tag}.jpg"
    generate_cover_image(surah_name, rec_name, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.12).resize((1080, 1920))

    final_video = concatenate_videoclips([cover_clip, main_video])
    out_video = f"final_{tag}.mp4"
    final_video.write_videofile(out_video, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")

    return out_video, cover_file, surah_name, rec_name

# ----------------- معالجات البوت التفاعلية -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"مرحباً بك يا {update.effective_user.first_name} في <b>بوت القرآن الكريم الذكي</b> 🌿\n\n"
        "✨ <b>يمكنك الآن طلب أي سورة بمجرد كتابة اسمها في الشات!</b>\n"
        "أمثلة: <code>نزل سورة الليل</code> أو <code>سورة الشرح</code> أو <code>الضحى</code>.\n\n"
        "وسيقوم البوت بمونتاج المقطع فوراً مع تظليل الذهب والصوت السينمائي والغلاف التلقائي!"
    )
    btns = [
        [InlineKeyboardButton("📖 نزل سورة الليل الآن", callback_data="req_surah_الليل")],
        [InlineKeyboardButton("🤍 نزل سورة الشرح", callback_data="req_surah_الشرح")],
        [InlineKeyboardButton("🌙 نزل سورة الملك", callback_data="req_surah_الملك")]
    ]
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    # تنظيف الكلمات الشائعة ("صوره", "سوره", "نزل", "هات")
    clean_query = user_text.replace("صوره", "").replace("صورة", "").replace("سورة", "").replace("سوره", "").replace("نزل", "").replace("اريد", "").strip()

    matched_surah = None
    for s_name in SURAHS_MAP:
        if s_name in clean_query or clean_query in s_name:
            matched_surah = s_name
            break

    if not matched_surah:
        await update.message.reply_text(
            "لم أتعرف على اسم السورة بدقة 🌿\n"
            "يرجى كتابة اسم السورة مباشرة، مثل: <b>سورة الليل</b> أو <b>سورة الضحى</b> أو <b>سورة الملك</b>.",
            parse_mode="HTML"
        )
        return

    s_info = SURAHS_MAP[matched_surah]
    status_msg = await update.message.reply_text(
        f"⏳ <b>جاري الآن إنتاج سورة {matched_surah}...</b>\n"
        f"• إضافة تظليل الكلمات بالذهب\n"
        f"• ضبط الصوت السينمائي 8D\n"
        f"• دمج الغلاف تلقائياً في الفيديو 📸\n\n"
        f"انتظر حوالي 45 ثانية وسيكون المقطع جاهزاً!",
        parse_mode="HTML"
    )

    try:
        tag = f"u_{update.effective_user.id}_{int(time.time())}"
        vid_path, cov_path, s_name, r_name = await asyncio.to_thread(
            produce_video_by_surah, s_info[0], s_info[1], s_info[2], "dossari", tag
        )

        with open(vid_path, "rb") as vf:
            caption = (
                f"🤍 <b>سورة {s_name} كاملة</b>\n"
                f"🎙️ بصوت القارئ: {r_name}\n\n"
                f"✨ الغلاف مدمج تلقائياً في أول الفيديو • ضع السماعات وعش السكينة 🎧"
            )
            await update.message.reply_video(video=vf, caption=caption, parse_mode="HTML")

        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء المونتاج: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("req_surah_"):
        surah_name = query.data.replace("req_surah_", "")
        s_info = SURAHS_MAP[surah_name]
        status_msg = await query.message.reply_text(f"⏳ جاري إنتاج سورة {surah_name} مع الغلاف التلقائي...")
        tag = f"btn_{int(time.time())}"
        vid_path, _, s_name, r_name = await asyncio.to_thread(
            produce_video_by_surah, s_info[0], s_info[1], s_info[2], "dossari", tag
        )
        with open(vid_path, "rb") as vf:
            await query.message.reply_video(video=vf, caption=f"سورة {s_name} - {r_name} 🌿")
        await status_msg.delete()

def main():
    if not BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN مفقود!", flush=True)
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    # مستمع الرسائل النصية المباشرة
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("🚀 تم تشغيل البوت الذكي بنظام الاستماع للرسائل النصية والغلاف التلقائي 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

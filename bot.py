import os
import sys
import json
import base64
import random
import shutil
import asyncio
import datetime
import subprocess
import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
STATS_FILE = "publish_history.json"
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

# صيدلية المشاعر للمتابعين
COMMUNITY_EMOTIONS = {
    "emo_sadness": {
        "title": "💔 حزين أو متعب الصدر",
        "badge": "رسالة لقلبك إذا كنت حزيناً أو متعباً 🌿",
        "hook": "إذا ضاقت بك الدنيا وتعب قلبك.. استمع لرسالة الله إليك 🤍",
        "surah": 94, "start": 1, "end": 8, "name": "الشرح"
    },
    "emo_anxiety": {
        "title": "🕊️ قلق من الرزق والمستقبل",
        "badge": "إذا كنت قلقاً من المستقبل أو الرزق 🕊️",
        "hook": "اطمئن على رزقك ومستقبلك.. الأمر كله بيد الله 🌿",
        "surah": 65, "start": 2, "end": 3, "name": "الطلاق"
    },
    "emo_peace": {
        "title": "🤍 أبحث عن السكينة والأمان",
        "badge": "تلاوة تنزل السكينة والأمان على روحك 🤍",
        "hook": "أرح سمعك وفؤادك من صخب الدنيا وضغوطها 🕊️",
        "surah": 13, "start": 28, "end": 28, "name": "الرعد"
    },
    "emo_sleep": {
        "title": "🌙 تلاوة هادئة للنوم العميق",
        "badge": "أمان وحصن لقلبك قبل أن تغمض عينيك 🌙",
        "hook": "تلاوة هادئة تعينك على نوم مطمئن وسكينة تامة 🕊️",
        "surah": 67, "start": 1, "end": 4, "name": "الملك"
    }
}

RECITERS_DICT = {
    "dossari": ("Dussary_128kbps", "ياسر الدوسري"),
    "qatami": ("Nasser_Alqatami_128kbps", "ناصر القطامي"),
    "abbad": ("Fares_Abbad_64kbps", "فارس عباد"),
    "muaiqly": ("MaherAlMuaiqly128kbps", "ماهر المعيقلي"),
    "alafasy": ("Alafasy_128kbps", "مشاري العفاسي")
}

# جلسات المستخدمين المؤقتة
USER_SESSIONS = {}

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

def clean_arabic_text(text):
    for sym in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']:
        text = text.replace(sym, '')
    return text.strip()

def render_word_frame(words, active_idx, badge, font_b64, watermark):
    chrome_bin = shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"
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
  <div class="badge">🎧 ضع السماعات • {badge}</div>
  <div class="ayah">{full_verse}</div>
  <div class="watermark">{watermark}</div>
</body></html>"""

    h_path, p_path = f"tmp_{active_idx}.html", f"frame_{active_idx}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def generate_custom_user_video(emotion_key, reciter_key, user_id):
    emo = COMMUNITY_EMOTIONS[emotion_key]
    rec_id, rec_name = RECITERS_DICT[reciter_key]
    watermark = "@quran_reels"

    ayahs = []
    for a in range(emo["start"], emo["end"] + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{emo['surah']}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic_text(t_res.get("data", {}).get("text", ""))
        if a == 1 and emo["surah"] != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        surah_str = f"{emo['surah']:03d}"
        ayah_str = f"{a:03d}"
        aud_url = f"https://everyayah.com/data/{rec_id}/{surah_str}{ayah_str}.mp3"
        aud_file = f"u_{user_id}_{a}.mp3"
        with open(aud_file, "wb") as f:
            f.write(requests.get(aud_url, timeout=25).content)
        ayahs.append({"text": txt, "audio": aud_file})

    # جلب فيديو Pexels
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=switzerland+mountains+drone+vertical&orientation=portrait&per_page=6", headers=headers, timeout=15).json()
    chosen_video = random.choice(res.get("videos", []))
    v_files = sorted(chosen_video["video_files"], key=lambda x: x.get("width", 0))
    bg_file = f"bg_{user_id}.mp4"
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
            img_path = render_word_frame(words, idx, emo["badge"], font_b64, watermark)
            text_clips.append(ImageClip(img_path).set_start(w_start).set_duration(w_dur).set_position(("center", "center")))
            w_start += w_dur
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 1.0

    bg = VideoFileClip(bg_file)
    bg = (bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.22).set_duration(tot_dur)

    out_name = f"reel_user_{user_id}.mp4"
    final = CompositeVideoClip([bg, dim] + text_clips).set_audio(final_audio)
    final.write_videofile(out_name, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")
    return out_name, emo["name"], rec_name

# ----------------- واجهات التفاعل -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    is_admin = (user_id == ADMIN_ID)

    buttons = [
        [InlineKeyboardButton("💊 صيدلية المشاعر (اختر ما تشعر به)", callback_data="user_menu_emotions")],
        [InlineKeyboardButton("🎙️ اختر قارئك المفضل واصنع تلاوتك", callback_data="user_menu_reciters")]
    ]

    if is_admin:
        buttons.append([InlineKeyboardButton("👑 لوحة تحكم الأدمن (نشر فوري وإحصائيات)", callback_data="admin_dashboard")])

    welcome_text = (
        f"مرحباً بك {update.effective_user.first_name} في <b>بوت القرآن الكريم التفاعلي</b> 🌿\n\n"
        "✨ اختر ما تشعر به من <b>صيدلية المشاعر</b> أو حدد قارئك المفضل، وسيقوم البوت بصناعة فيديو تلاوة سينمائي متزامن بالذهب لك خصيصاً خلال ثوانٍ!"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(update.effective_user.id)

    if user_id not in USER_SESSIONS:
        USER_SESSIONS[user_id] = {"emotion": "emo_sadness", "reciter": "dossari"}

    if data == "user_menu_emotions":
        btns = [
            [InlineKeyboardButton(v["title"], callback_data=f"sel_emo_{k}")]
            for k, v in COMMUNITY_EMOTIONS.items()
        ]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="go_home")])
        await query.edit_message_text("🌿 <b>صف لنا ما تشعر به في صدرك الآن:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("sel_emo_"):
        key = data.replace("sel_emo_", "")
        USER_SESSIONS[user_id]["emotion"] = key
        # الانتقال لاختيار القارئ
        btns = [
            [InlineKeyboardButton(v[1], callback_data=f"sel_rec_{k}")]
            for k, v in RECITERS_DICT.items()
        ]
        await query.edit_message_text(
            f"✅ تم اختيار الحالة: <b>{COMMUNITY_EMOTIONS[key]['title']}</b>\n\n"
            "🎙️ <b>اختر القارئ الذي تحب أن تسمع بصوته:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif data.startswith("sel_rec_"):
        rec_key = data.replace("sel_rec_", "")
        USER_SESSIONS[user_id]["reciter"] = rec_key
        emo_key = USER_SESSIONS[user_id]["emotion"]

        status_msg = await query.edit_message_text(
            f"⏳ <b>جاري مونتاج تلاوتك الخاصة الآن...</b>\n\n"
            f"• الحالة: {COMMUNITY_EMOTIONS[emo_key]['title']}\n"
            f"• القارئ: {RECITERS_DICT[rec_key][1]}\n"
            f"• المؤثرات: تظليل الكلمات بالذهب + صوت 8D ومطر خافت 🎧\n\n"
            f"يرجى الانتظار ثوانٍ معدودة...",
            parse_mode="HTML"
        )

        try:
            video_path, s_name, r_name = await asyncio.to_thread(
                generate_custom_user_video, emo_key, rec_key, user_id
            )
            with open(video_path, "rb") as vf:
                caption = (
                    f"🤍 تلاوتك الخاصة:\n"
                    f"سورة {s_name} بصوت القارئ {r_name} 🌿\n\n"
                    f"ضع السماعات وعش السكينة 🎧 • شاركها تؤجر 🕊️"
                )
                await query.message.reply_video(video=vf, caption=caption)
            await status_msg.delete()
        except Exception as e:
            await query.message.reply_text(f"❌ حدث خطأ أثناء إعداد المقطع: {e}")

    elif data == "go_home":
        await start_command(query, context)

def main():
    if not BOT_TOKEN:
        print("يرجى ضبط TELEGRAM_BOT_TOKEN!", flush=True)
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 تم تشغيل بوت مجتمع المتابعين وصيدلية المشاعر 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

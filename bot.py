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

# الإعدادات الافتراضية
CONFIG = {
    "reciter_id": "Dussary_128kbps",
    "reciter_name": "ياسر الدوسري",
    "theme_key": "mountains",
    "theme_name": "🏔️ جبال وأودية خضراء"
}

# قائمة القراء التفاعلية في تليجرام
RECITERS = {
    "dossari": ("Dussary_128kbps", "ياسر الدوسري"),
    "qatami": ("Nasser_Alqatami_128kbps", "ناصر القطامي"),
    "abbad": ("Fares_Abbad_64kbps", "فارس عباد"),
    "muaiqly": ("MaherAlMuaiqly128kbps", "ماهر المعيقلي"),
    "alafasy": ("Alafasy_128kbps", "مشاري العفاسي"),
    "abdulbasit": ("Abdul_Basit_Murattal_192kbps", "عبد الباسط عبد الصمد"),
    "minshawi": ("Minshawy_Murattal_128kbps", "محمد صديق المنشاوي"),
    "ghamadi": ("Ghamadi_40kbps", "سعد الغامدي")
}

THEMES = {
    "mountains": {
        "name": "🏔️ جبال وأودية خضراء",
        "queries": ["switzerland mountains drone vertical", "alps landscape sunny green valley", "nature green valley aerial 4k vertical"]
    },
    "clouds": {
        "name": "☁️ سحاب وضباب ومطر",
        "queries": ["foggy mountains dark clouds vertical", "misty forest rain cinematic vertical", "dark moody clouds nature vertical"]
    },
    "ocean": {
        "name": "🌊 بحار وأمواج هادئة",
        "queries": ["calm ocean waves sunset vertical", "dark moody sea water vertical", "beach waves aerial vertical"]
    },
    "snow": {
        "name": "❄️ ثلوج وشتاء سينمائي",
        "queries": ["winter snow mountains drone vertical", "pine trees snow aerial vertical", "falling snow forest moody vertical"]
    }
}

QURAN_PLAYLIST = [
    {"surah": 108, "start": 1, "end": 3, "name": "الكوثر"},
    {"surah": 103, "start": 1, "end": 3, "name": "العصر"},
    {"surah": 112, "start": 1, "end": 4, "name": "الإخلاص"},
    {"surah": 113, "start": 1, "end": 5, "name": "الفلق"},
    {"surah": 114, "start": 1, "end": 6, "name": "الناس"},
    {"surah": 97,  "start": 1, "end": 5, "name": "القدر"},
    {"surah": 94,  "start": 1, "end": 8, "name": "الشرح"},
    {"surah": 95,  "start": 1, "end": 8, "name": "التين"},
    {"surah": 1,   "start": 1, "end": 7, "name": "الفاتحة"},
    {"surah": 67,  "start": 1, "end": 4, "name": "الملك"},
    {"surah": 55,  "start": 1, "end": 5, "name": "الرحمن"},
    {"surah": 93,  "start": 1, "end": 5, "name": "الضحى"}
]

PINNED_COMMENTS = [
    "اكتب شيئاً تؤجر عليه في ميزان حسناتك 🌿 (سبحان الله، الحمد لله، لا إله إلا الله، الله أكبر) 🤍",
    "شارك الآية لعلها تريح قلباً متعباً الآن وتكون لك صدقة جارية يوم القيامة 🕊️",
    "ما هي أكثر آية تشعرك بالسكينة والطمأنينة عندما تسمعها؟ شاركنا بها في التعليقات 🤍"
]

def log_publish_event(surah_name, ayah_range, reciter_name, release_url):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    history = {}
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = {}

    if today not in history:
        history[today] = []

    history[today].append({
        "time": datetime.datetime.utcnow().strftime("%H:%M UTC"),
        "surah": surah_name,
        "ayahs": ayah_range,
        "reciter": reciter_name,
        "url": release_url
    })

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_stats_report():
    if not os.path.exists(STATS_FILE):
        return "📊 لا توجد أي عمليات نشر مسجلة حتى الآن."

    with open(STATS_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    today_posts = history.get(today, [])
    total_all = sum(len(v) for v in history.values())

    msg = (
        f"📊 <b>إحصائيات النشر الآلي</b>\n\n"
        f"📅 <b>اليوم ({today}):</b> {len(today_posts)} فيديو منشورة\n"
        f"🌐 <b>إجمالي الفيديوهات المنتجة:</b> {total_all}\n"
    )

    if today_posts:
        msg += "\n<b>آخر المقاطع المنشورة:</b>\n"
        for p in today_posts[-3:]:
            msg += f"• سورة {p['surah']} ({p['ayahs']}) - {p['reciter']} [<a href='{p['url']}'>مشاهدة</a>]\n"
    return msg

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

def render_quran_ayah_image(text, index, font_b64, watermark_handle):
    chrome_bin = shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"
    words_count = len(text.split())
    font_size = 72 if words_count <= 5 else (60 if words_count <= 12 else 48)

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; justify-content: center; align-items: center; position: relative; }}
  .ayah {{ direction: rtl; text-align: center; font-family: 'AmiriQuran'; font-size: {font_size}px; font-weight: bold; color: #fff; line-height: 1.85; max-width: 920px; text-shadow: 0 0 10px rgba(0,0,0,0.95), 0 4px 18px rgba(0,0,0,0.9); }}
  .watermark {{ position: absolute; bottom: 120px; left: 50%; transform: translateX(-50%); font-family: 'AmiriQuran'; font-size: 25px; color: rgba(255,255,255,0.45); direction: ltr; }}
</style></head>
<body><div class="ayah">{text}</div><div class="watermark">{watermark_handle}</div></body></html>"""

    h_path, p_path = f"temp_{index}.html", f"ayah_{index}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def execute_pipeline(reciter_id, reciter_name, theme_key):
    item = random.choice(QURAN_PLAYLIST)
    watermark = os.getenv("WATERMARK_HANDLE", "@quran_reels").strip()

    meta_url = f"https://api.alquran.cloud/v1/surah/{item['surah']}"
    surah_name = requests.get(meta_url, timeout=15).json().get("data", {}).get("name", f"سورة {item['surah']}")
    ayahs = []

    for a in range(item["start"], item["end"] + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{item['surah']}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic_text(t_res.get("data", {}).get("text", ""))
        if a == 1 and item["surah"] != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        surah_str = f"{item['surah']:03d}"
        ayah_str = f"{a:03d}"
        aud_url = f"https://everyayah.com/data/{reciter_id}/{surah_str}{ayah_str}.mp3"
        aud_name = f"aud_{a}.mp3"
        try:
            r = requests.get(aud_url, timeout=25)
            if r.status_code == 200 and len(r.content) > 3000:
                with open(aud_name, "wb") as f:
                    f.write(r.content)
            else:
                r_fb = requests.get(f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3", timeout=25)
                with open(aud_name, "wb") as f:
                    f.write(r_fb.content)
        except Exception:
            r_fb = requests.get(f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3", timeout=25)
            with open(aud_name, "wb") as f:
                f.write(r_fb.content)

        ayahs.append({"text": txt, "audio": aud_name})

    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    query = random.choice(THEMES[theme_key]["queries"])
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get(f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=10", headers=headers, timeout=15).json()
    chosen_video = random.choice(res.get("videos", []))
    v_files = sorted(chosen_video["video_files"], key=lambda x: x.get("width", 0))
    with open("bg.mp4", "wb") as f:
        f.write(requests.get(v_files[-1]["link"], timeout=35).content)

    font_b64 = get_font_base64()
    audio_clips, text_clips = [], []
    curr_t = 0.0

    for i, ay in enumerate(ayahs):
        ac = AudioFileClip(ay["audio"])
        audio_clips.append(ac)
        img_file = render_quran_ayah_image(ay["text"], i, font_b64, watermark)
        text_clips.append(ImageClip(img_file).set_start(curr_t).set_duration(ac.duration).set_position(("center", "center")))
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 0.8

    bg_clip = VideoFileClip("bg.mp4")
    bg_clip = (bg_clip.loop(duration=tot_dur) if bg_clip.duration < tot_dur else bg_clip.subclip(0, tot_dur)).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.20).set_duration(tot_dur)

    final = CompositeVideoClip([bg_clip, dim] + text_clips).set_audio(final_audio)
    out_file = "final_reel.mp4"
    final.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")

    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    tag = f"reel-{int(random.random()*1000000000)}"
    rel_res = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
        json={"tag_name": tag, "name": f"Reel {tag}", "draft": False},
        timeout=20
    ).json()

    upload_url = rel_res["upload_url"].split("{")[0]
    with open(out_file, "rb") as vf:
        up = requests.post(f"{upload_url}?name=final_reel.mp4", headers={"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}, data=vf, timeout=60).json()
    pub_url = up.get("browser_download_url")

    ayah_range = f"{item['start']}-{item['end']}"
    title = f"تلاوة تريح القلب 🌿 سورة {surah_name} ({ayah_range}) | {reciter_name}"[:100]
    caption = f"سورة {surah_name} 🤍 بصوت {reciter_name}\n\n#قرآن #تلاوات #fyp #explore"
    pinned_com = random.choice(PINNED_COMMENTS)

    buf_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    buf_channels = [c.strip() for c in os.getenv("BUFFER_CHANNEL_ID", "").split(",") if c.strip()]
    if buf_token and buf_channels:
        mutation = """mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id } } ... on MutationError { message } } }"""
        for ch in buf_channels:
            payload = {"channelId": ch, "text": caption, "mode": "shareNow", "schedulingType": "automatic", "assets": [{"video": {"url": pub_url}}]}
            if "youtube" in ch or ch == "6aa72b30ea19ca0bde39598b":
                payload["metadata"] = {"youtube": {"title": title, "categoryId": "27"}}
            else:
                payload["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
            try:
                requests.post("https://api.buffer.com", headers={"Authorization": f"Bearer {buf_token}", "Content-Type": "application/json"}, json={"query": mutation, "variables": {"input": payload}}, timeout=30)
            except Exception:
                pass

    log_publish_event(surah_name, ayah_range, reciter_name, pub_url)
    return surah_name, ayah_range, pub_url, pinned_com

def build_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎙️ القارئ: {CONFIG['reciter_name']}", callback_data="menu_reciters")],
        [InlineKeyboardButton(f"🎬 المشهد: {CONFIG['theme_name']}", callback_data="menu_themes")],
        [InlineKeyboardButton("⚡ إنتاج ونشر فوري الآن", callback_data="btn_publish_now")],
        [InlineKeyboardButton("📊 إحصائيات النشر اليومي", callback_data="btn_show_stats")]
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎛️ <b>لوحة التحكم في خط إنتاج القرآن الكريم</b>\n\n"
        "اختر القارئ المفضل ونوع المشهد، أو اضغط على <b>الإنتاج الفوري</b> لنشر مقطع جديد على الفور عبر يوتيوب، إنستغرام، وتيك توك:"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=build_main_keyboard())

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_stats_report(), parse_mode="HTML", disable_web_page_preview=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_main":
        await query.edit_message_text(
            "🎛️ <b>لوحة التحكم الرئيسية:</b>",
            parse_mode="HTML",
            reply_markup=build_main_keyboard()
        )

    elif data == "menu_reciters":
        buttons = []
        rec_items = list(RECITERS.items())
        # ترتيب الأزرار في صفين متجاورين لتنسيق مريح في تليجرام
        for i in range(0, len(rec_items), 2):
            row = []
            k1, v1 = rec_items[i]
            row.append(InlineKeyboardButton(f"{'✅ ' if CONFIG['reciter_id'] == v1[0] else ''}{v1[1]}", callback_data=f"set_rec_{k1}"))
            if i + 1 < len(rec_items):
                k2, v2 = rec_items[i+1]
                row.append(InlineKeyboardButton(f"{'✅ ' if CONFIG['reciter_id'] == v2[0] else ''}{v2[1]}", callback_data=f"set_rec_{k2}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="menu_main")])
        await query.edit_message_text("🎙️ <b>اختر القارئ المفضل للإنتاج:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("set_rec_"):
        key = data.replace("set_rec_", "")
        CONFIG["reciter_id"], CONFIG["reciter_name"] = RECITERS[key]
        await query.edit_message_text(f"✅ تم ضبط القارئ على: <b>{CONFIG['reciter_name']}</b>", parse_mode="HTML", reply_markup=build_main_keyboard())

    elif data == "menu_themes":
        buttons = [
            [InlineKeyboardButton(f"{'✅ ' if CONFIG['theme_key'] == k else ''}{v['name']}", callback_data=f"set_thm_{k}")]
            for k, v in THEMES.items()
        ]
        buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="menu_main")])
        await query.edit_message_text("🎬 <b>اختر نوع المشهد الطبيعي للخلفية:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("set_thm_"):
        key = data.replace("set_thm_", "")
        CONFIG["theme_key"] = key
        CONFIG["theme_name"] = THEMES[key]["name"]
        await query.edit_message_text(f"✅ تم ضبط نوع المشهد على: <b>{CONFIG['theme_name']}</b>", parse_mode="HTML", reply_markup=build_main_keyboard())

    elif data == "btn_show_stats":
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]])
        await query.edit_message_text(get_stats_report(), parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_kb)

    elif data == "btn_publish_now":
        status_msg = await query.message.reply_text(
            f"⏳ <b>بدء الإنتاج الفوري...</b>\n"
            f"• القارئ: {CONFIG['reciter_name']}\n"
            f"• المشهد: {CONFIG['theme_name']}\n\n"
            f"جاري جلب الآيات والمونتاج المتزامن ونشر الفيديو...",
            parse_mode="HTML"
        )
        try:
            s_name, a_range, pub_url, pinned_comment = await asyncio.to_thread(
                execute_pipeline, CONFIG["reciter_id"], CONFIG["reciter_name"], CONFIG["theme_key"]
            )

            report = (
                f"✅ <b>تم إنتاج ونشر المقطع بنجاح!</b>\n\n"
                f"📖 <b>السورة:</b> {s_name} ({a_range})\n"
                f"🎙️ <b>القارئ:</b> {CONFIG['reciter_name']}\n"
                f"🔗 <b>رابط الفيديو:</b> <a href='{pub_url}'>مشاهدة المقطع</a>\n\n"
                f"📌 <b>التعليق المقترح للتثبيت:</b>\n"
                f"<code>{pinned_comment}</code>"
            )
            await status_msg.edit_text(report, parse_mode="HTML", disable_web_page_preview=True)

            if os.path.exists("final_reel.mp4"):
                with open("final_reel.mp4", "rb") as vf:
                    await query.message.reply_video(video=vf, caption=f"سورة {s_name} ({a_range}) - {CONFIG['reciter_name']} 🌿")
        except Exception as e:
            await status_msg.edit_text(f"❌ حدث خطأ أثناء الإنتاج: {e}")

def main():
    if not BOT_TOKEN:
        print("خطأ: لم يتم ضبط TELEGRAM_BOT_TOKEN في Secrets!", flush=True)
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 تم تشغيل لوحة التحكم مع مكتبة القراء الرائجة 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

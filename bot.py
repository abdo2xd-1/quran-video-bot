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

# ذاكرة المحادثة لكل مستخدم ليتحدث معك جمناي كشات طبيعي
USER_CONVERSATIONS = {}

# روابط السور الكاملة عالية الجودة من سيرفرات MP3Quran المباشرة
FULL_SURAHS_SERVERS = {
    "dossari": "https://server11.mp3quran.net/yasser/{:03d}.mp3",
    "alafasy": "https://server8.mp3quran.net/afs/{:03d}.mp3",
    "qatami": "https://server6.mp3quran.net/qtm/{:03d}.mp3",
    "minshawi": "https://server10.mp3quran.net/minsh/{:03d}.mp3"
}

RECITERS_SHORTS = {
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

# ----------------- 1. محرك Gemini الذكي وتحديد الأوامر (Tool Calling) -----------------
def call_gemini_agent(user_id, user_text):
    """إرسال المحادثة إلى Gemini مع تعريف الأدوات التي يمكن لـ Gemini استدعاؤها"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

    if user_id not in USER_CONVERSATIONS:
        USER_CONVERSATIONS[user_id] = []

    USER_CONVERSATIONS[user_id].append({"role": "user", "parts": [{"text": user_text}]})
    # الاحتفاظ بآخر 8 رسائل فقط للحفاظ على سرعة الرد
    if len(USER_CONVERSATIONS[user_id]) > 8:
        USER_CONVERSATIONS[user_id] = USER_CONVERSATIONS[user_id][-8:]

    tools_schema = [
        {
            "functionDeclarations": [
                {
                    "name": "create_quran_video",
                    "description": "استدعِ هذه الأداة إذا طلب المستخدم إنتاج فيديو للقرآن الكريم (سواء سورة كاملة أو شورتس).",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "surah_name": {"type": "STRING", "description": "اسم السورة بالعربية (مثل: الكهف، الملك، الشرح)"},
                            "surah_number": {"type": "INTEGER", "description": "رقم السورة من 1 إلى 114"},
                            "is_full_surah": {"type": "BOOLEAN", "description": "اجعلها True إذا طلب المستخدم السورة كاملة صراحة"},
                            "start_ayah": {"type": "INTEGER", "description": "آية البداية إذا كان المقطع شورتس"},
                            "end_ayah": {"type": "INTEGER", "description": "آية النهاية إذا كان المقطع شورتس"},
                            "reciter": {"type": "STRING", "description": "اسم القارئ (dossari, alafasy, qatami, minshawi)"}
                        },
                        "required": ["surah_name", "surah_number", "is_full_surah"]
                    }
                },
                {
                    "name": "create_general_video",
                    "description": "استدعِ هذه الأداة إذا طلب المستخدم فيديو في أي موضوع عام (فضاء، تحفيز، معلومات عامة، علم نفس، تاريخ، إلخ).",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING", "description": "عنوان جذاب للفيديو"},
                            "badge": {"type": "STRING", "description": "عبارة البادج العلوي"},
                            "script_sentences": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "سيناريو الإلقاء الصوتي باللغة العربية الفصحى (3 إلى 4 جمل مشوقة)"
                            },
                            "search_keywords": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "كلمات بحث إنجليزية عمودية لـ Pexels لكل جملة"
                            }
                        },
                        "required": ["title", "badge", "script_sentences", "search_keywords"]
                    }
                }
            ]
        }
    ]

    payload = {
        "contents": USER_CONVERSATIONS[user_id],
        "tools": tools_schema,
        "systemInstruction": {
            "parts": [{
                "text": (
                    "أنت جيميني (Gemini)، المساعد الذكي وصانع المحتوى الرئيسي للمستخدم. "
                    "تحدث معه بطبيعية تامة وود واحترام (باللهجة المصرية أو الفصحى حسب أسلوبه). "
                    "إذا كان يسأل سؤالاً عادياً أو يدردش معك، أجب عليه كشات ذكاء اصطناعي طبيعي. "
                    "إذا طلب منك إنتاج فيديو قرآن (مثال: سورة الكهف كاملة، أو شورتس)، استدعِ create_quran_video. "
                    "انتبه جيداً: إذا ذكر كلمة 'كاملة' أو طلب سورة الكهف كاملة، اجعل is_full_surah=True فوراً. "
                    "إذا طلب أي موضوع عام (فضاء، علم، تحفيز)، استدعِ create_general_video واكتب له السيناريو المناسب."
                )
            }]
        }
    }

    try:
        res = requests.post(url, json=payload, timeout=25).json()
        candidate = res.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0]
        
        # إذا قرر جمناي استدعاء أداة
        if "functionCall" in candidate:
            fn_call = candidate["functionCall"]
            return {"type": "tool", "name": fn_call["name"], "args": fn_call["args"]}
        
        # إذا كان رداً حوارياً عادياً
        reply_text = candidate.get("text", "أنا معاك يا غالي، أؤمرني تحب نعمل إيه؟ 🤍")
        USER_CONVERSATIONS[user_id].append({"role": "model", "parts": [{"text": reply_text}]})
        return {"type": "chat", "text": reply_text}
    except Exception as e:
        print(f"Gemini API Error: {e}", flush=True)
        return {"type": "chat", "text": "أهلاً بك! حدث خطأ في الاتصال بـ Gemini، أعد إرسال رسالتك وسأنفذها فوراً 🤍"}

# ----------------- 2. إنتاج سورة كاملة (Long-Form) -----------------
def generate_full_surah_audio_and_video(surah_num, surah_name, reciter_key, tag):
    """تنزيل التلاوة الكاملة المباشرة بدون تقطيع ومونتاجها مع الغلاف"""
    rec_key = reciter_key if reciter_key in FULL_SURAHS_SERVERS else "alafasy"
    rec_name = RECITERS_SHORTS.get(rec_key, ("Alafasy", "مشاري العفاسي"))[1]
    
    # تحميل التلاوة الكاملة من سيرفر MP3Quran المباشر
    audio_url = FULL_SURAHS_SERVERS[rec_key].format(surah_num)
    aud_file = f"full_surah_{tag}.mp3"
    
    r = requests.get(audio_url, timeout=45)
    with open(aud_file, "wb") as f:
        f.write(r.content)

    # توليد الغلاف المربع الرسمي
    cover_file = f"cover_full_{tag}.jpg"
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
<body><div class="box"><div class="circle"></div><div class="badge">🕌 تلاوة خاشعة كاملة 🌿</div><div class="title">سُورَةُ {surah_name} كَامِلَةً</div><div class="reciter">بصوت القارئ {reciter_name}</div></div></body></html>"""

    with open("tmp_cov.html", "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", f"--screenshot={os.path.abspath(cover_file)}", f"file://{os.path.abspath('tmp_cov.html')}"], check=True)

    return aud_file, cover_file, rec_name

# ----------------- 3. إنتاج مقاطع الشورتس والمحتوى العام -----------------
def generate_shorts_video(surah_num, surah_name, start_a, end_a, reciter_key, tag):
    rec_info = RECITERS_SHORTS.get(reciter_key, RECITERS_SHORTS["alafasy"])
    rec_id, rec_name = rec_info
    
    ayahs = []
    font_b64 = get_font_base64()
    chrome_bin = get_chrome()

    for a in range(start_a, end_a + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=15).json()
        txt = t_res.get("data", {}).get("text", "")
        if a == 1 and surah_num != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        aud_file = f"aud_{tag}_{a}.mp3"
        # خوادم EveryAyah المؤكدة
        surah_str, ayah_str = f"{surah_num:03d}", f"{a:03d}"
        url = f"https://everyayah.com/data/{rec_id}/{surah_str}{ayah_str}.mp3"
        r = requests.get(url, timeout=20)
        if r.status_code != 200 or len(r.content) < 4000:
            # بديل مباشر العفاسي
            r = requests.get(f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3", timeout=20)
        with open(aud_file, "wb") as f:
            f.write(r.content)
        ayahs.append({"text": txt, "audio": aud_file})

    # خلفية طبيعية
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=foggy+mountains+drone+vertical&orientation=portrait&per_page=5", headers=headers, timeout=15).json()
    v_link = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))[-1]["link"]
    bg_file = f"bg_{tag}.mp4"
    with open(bg_file, "wb") as f:
        f.write(requests.get(v_link, timeout=35).content)

    audio_clips, text_clips = [], []
    curr_t = 0.0

    for idx, ay in enumerate(ayahs):
        ac = AudioFileClip(ay["audio"])
        audio_clips.append(ac)
        
        # بطاقة الآية
        html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; margin: 0; }}
  .badge {{ position: absolute; top: 190px; background: rgba(10,14,20,0.65); border: 1px solid rgba(212,175,55,0.45); color: #fff; font-family: 'Amiri'; font-size: 26px; padding: 10px 28px; border-radius: 30px; }}
  .ayah {{ text-align: center; font-family: 'Amiri'; font-size: 54px; font-weight: bold; line-height: 1.9; max-width: 920px; color: #fff; text-shadow: 0 0 14px rgba(0,0,0,0.95); }}
</style></head>
<body><div class="badge">سورة {surah_name} 🌿</div><div class="ayah">{ay['text']}</div></body></html>"""
        with open("tmp_a.html", "w", encoding="utf-8") as f:
            f.write(html)
        p_path = f"frame_{tag}_{idx}.png"
        subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath('tmp_a.html')}"], check=True)
        
        text_clips.append(ImageClip(p_path).set_start(curr_t).set_duration(ac.duration).set_position(("center", "center")))
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 0.8
    bg = VideoFileClip(bg_file).loop(duration=tot_dur).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.22).set_duration(tot_dur)

    out_video = f"final_sh_{tag}.mp4"
    CompositeVideoClip([bg, dim] + text_clips).set_audio(final_audio).write_videofile(out_video, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")
    return out_video, rec_name

# ----------------- 4. استقبال رسائل تليجرام وإدارتها عبر Gemini -----------------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # استدعاء Gemini ليفكر ويقرر الرد أو الأداة
    decision = await asyncio.to_thread(call_gemini_agent, user_id, user_text)

    # 1. إذا كان مجرد حوار عادي أو استفسار
    if decision["type"] == "chat":
        await update.message.reply_text(decision["text"])
        return

    # 2. إذا قرر Gemini تنفيذ أمر إنتاج فيديو
    tool_name = decision["name"]
    args = decision["args"]
    tag = f"run_{user_id}_{int(time.time())}"

    if tool_name == "create_quran_video":
        s_name = args.get("surah_name", "الكهف")
        s_num = args.get("surah_number", 18)
        is_full = args.get("is_full_surah", False)
        reciter = args.get("reciter", "dossari")

        if is_full:
            # تنفيذ طلب السورة كاملة بدون تقطيع
            status_msg = await update.message.reply_text(
                f"🕌 <b>أمر من Gemini:</b> جاري تجهيز <b>سورة {s_name} كاملة</b> بصوت القارئ المفضل لديك الآن 🤍\n"
                f"يتم جلب التلاوة الكاملة وتجهيز الغلاف الرسمي...",
                parse_mode="HTML"
            )
            try:
                aud_file, cov_file, r_name = await asyncio.to_thread(
                    generate_full_surah_audio_and_video, s_num, s_name, reciter, tag
                )
                with open(aud_file, "rb") as af, open(cov_file, "rb") as cf:
                    caption = f"🕌 <b>سورة {s_name} كاملة</b>\n🎙️ بصوت: {r_name}\n\nنور ما بين الجمعتين وسكينة لقلبك 🌿"
                    await update.message.reply_audio(audio=af, thumbnail=cf, title=f"سورة {s_name} كاملة", performer=r_name, caption=caption, parse_mode="HTML")
                await status_msg.delete()
            except Exception as e:
                await status_msg.edit_text(f"❌ حدث خطأ: {e}")
        else:
            # تنفيذ طلب مقطع شورتس
            start_a = args.get("start_ayah", 1)
            end_a = args.get("end_ayah", 6)
            status_msg = await update.message.reply_text(f"🎬 <b>أمر من Gemini:</b> جاري إنتاج مقطع شورتس لسورة {s_name} ({start_a}-{end_a})...", parse_mode="HTML")
            try:
                vid_file, r_name = await asyncio.to_thread(
                    generate_shorts_video, s_num, s_name, start_a, end_a, reciter, tag
                )
                with open(vid_file, "rb") as vf:
                    await update.message.reply_video(video=vf, caption=f"سورة {s_name} ({start_a}-{end_a}) بصوت {r_name} 🤍")
                await status_msg.delete()
            except Exception as e:
                await status_msg.edit_text(f"❌ حدث خطأ: {e}")

    elif tool_name == "create_general_video":
        title = args.get("title", "فيديو اليوم")
        await update.message.reply_text(f"🚀 <b>أمر من Gemini:</b> جاري إنتاج فيديو بالذكاء الاصطناعي بعنوان: <b>{title}</b>...", parse_mode="HTML")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        f"أهلاً بك يا {update.effective_user.first_name}! أنا <b>Gemini AI</b> وأنا المدير المباشر هنا 🤖\n\n"
        "تحدث معي بأي أسلوب تريده، اسألني، ناقشني، أو اطلب مني إنتاج أي فيديو:\n"
        "• <i>«نزلي سورة الكهف كاملة»</i>\n"
        "• <i>«اعملي شورتس لسورة الملك»</i>\n"
        "• <i>«اعملي فيديو عن أسرار الفضاء»</i>\n\n"
        "أنا من يفهمك وأنا من يصدر الأوامر للنظام فوراً 🤍"
    )
    await update.message.reply_text(welcome, parse_mode="HTML")

def main():
    if not BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN مفقود!", flush=True)
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    print("🚀 تم تشغيل البوت المربوط بعقل Gemini AI بنجاح 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

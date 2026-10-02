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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

RECITERS = {
    "dossari": ("Dussary_128kbps", "ياسر الدوسري"),
    "qatami": ("Nasser_Alqatami_128kbps", "ناصر القطامي"),
    "abbad": ("Fares_Abbad_64kbps", "فارس عباد"),
    "muaiqly": ("MaherAlMuaiqly128kbps", "ماهر المعيقلي"),
    "alafasy": ("Alafasy_128kbps", "مشاري العفاسي"),
    "minshawi": ("Minshawy_Murattal_128kbps", "محمد صديق المنشاوي")
}

# ----------------- عقل الذكاء الاصطناعي (Gemini AI Parser) -----------------
def analyze_with_ai(user_prompt):
    """تحليل أي كلام يرسله المستخدم لتحديد نية الطلب والسورة والآيات المناسبة"""
    if not GEMINI_KEY:
        # نظام احتياطي في حال عدم إدخال المفتاح
        return {"action": "generate", "surah": 94, "start": 1, "end": 8, "reciter": "dossari", "reply": "أرح صدرك بآيات سورة الشرح 🤍"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    system_instruction = (
        "أنت العقل المدبر لقناة قرآن كريم احترافية. المستخدم يرسل لك كلاماً حراً (فضفضة، مشاعر، رغبة في سورة معينة، أو استفسار). "
        "مهمتك: "
        "1. الرد عليه بلطف وأسلوب إيماني راقٍ ومختصر (سطر واحد فقط) يحتوي على دعاء أو طمأنينة. "
        "2. تحديد السورة ورقمها، ورقم آية البداية والنهاية (بما يناسب مقطع ريلز قصير من 3 إلى 8 آيات)، والقارئ المناسب (dossari, qatami, abbad, muaiqly, alafasy, minshawi). "
        "أرجع النتيجة بصيغة JSON فقط بهذا الشكل الصارم دون أي نصوص إضافية:\n"
        "{\"action\": \"generate\", \"surah\": 94, \"start\": 1, \"end\": 8, \"reciter\": \"dossari\", \"surah_name\": \"الشرح\", \"reply\": \"كلامك الجميل هنا 🤍\"}"
    )

    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nرسالة المستخدم: {user_prompt}"}]}],
        "generationConfig": {"temperature": 0.3}
    }

    try:
        res = requests.post(url, json=payload, timeout=15).json()
        raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        # تنظيف علامات كود الماركداون
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        print(f"AI Parse Error: {e}", flush=True)
        return {"action": "generate", "surah": 94, "start": 1, "end": 8, "reciter": "dossari", "surah_name": "الشرح", "reply": "أرح سمعك وفؤادك بآيات الله 🤍"}

# ----------------- محرك المونتاج والغلاف التلقائي -----------------
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

def download_audio_safe(surah_num, ayah_num, rec_id, out_file):
    surah_str = f"{surah_num:03d}"
    ayah_str = f"{ayah_num:03d}"
    urls = [
        f"https://everyayah.com/data/{rec_id}/{surah_str}{ayah_str}.mp3",
        f"https://everyayah.com/data/Yasser_Ad-Dussary_128kbps/{surah_str}{ayah_str}.mp3",
        f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3"
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=20)
            if r.status_code == 200 and len(r.content) > 4000:
                with open(out_file, "wb") as f:
                    f.write(r.content)
                return True
        except Exception:
            continue
    return False

def render_quran_frame(words, active_idx, font_b64):
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
  <div class="badge">🎧 ضع السماعات • سكينة وطمأنينة لقلبك 🌿</div>
  <div class="ayah">{full_verse}</div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path, p_path = f"tmp_{active_idx}.html", f"frame_{active_idx}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def generate_cover_image(surah_name, reciter_name, font_b64, output_path="auto_cover.jpg"):
    chrome_bin = shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; position: relative; }}
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
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(output_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return output_path

def produce_video_pipeline(surah_num, start_a, end_a, reciter_key="dossari", tag="ai"):
    rec_id, rec_name = RECITERS.get(reciter_key, RECITERS["dossari"])
    meta = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}", timeout=15).json()
    surah_name = meta.get("data", {}).get("name", f"سورة {surah_num}").replace("سورة ", "")

    ayahs = []
    for a in range(start_a, end_a + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic(t_res.get("data", {}).get("text", ""))
        if a == 1 and surah_num != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        aud_file = f"aud_{tag}_{a}.mp3"
        download_audio_safe(surah_num, a, rec_id, aud_file)
        ayahs.append({"text": txt, "audio": aud_file})

    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=switzerland+mountains+drone+vertical&orientation=portrait&per_page=6", headers=headers, timeout=15).json()
    v_files = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))
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

    cover_file = f"cover_{tag}.jpg"
    generate_cover_image(surah_name, rec_name, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.12).resize((1080, 1920))

    temp_joined = f"temp_{tag}.mp4"
    joined_video = concatenate_videoclips([cover_clip, main_video])
    joined_video.write_videofile(temp_joined, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")

    out_video = f"final_{tag}.mp4"
    embed_cmd = ["ffmpeg", "-y", "-i", temp_joined, "-i", cover_file, "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic", out_video]
    try:
        subprocess.run(embed_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        out_video = temp_joined

    return out_video, cover_file, surah_name, rec_name

# ----------------- معالجة أي رسالة نصية بالذكاء الاصطناعي -----------------
async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text.strip()
    status_msg = await update.message.reply_text("🤖 <i>جاري تحليل رسالتك وفهم نيتك بالذكاء الاصطناعي...</i>", parse_mode="HTML")

    # تحليل الرسالة عبر الذكاء الاصطناعي
    ai_result = await asyncio.to_thread(analyze_with_ai, user_prompt)
    ai_reply = ai_result.get("reply", "أبشر بكل خير 🤍")
    surah_num = ai_result.get("surah", 94)
    start_a = ai_result.get("start", 1)
    end_a = ai_result.get("end", 5)
    reciter_key = ai_result.get("reciter", "dossari")

    await status_msg.edit_text(
        f"🤍 <b>{ai_reply}</b>\n\n"
        f"🎬 <b>جاري بدء الإنتاج الآلي لمقطعك:</b>\n"
        f"• السورة: رقم {surah_num} (الآيات {start_a} إلى {end_a})\n"
        f"• القارئ: {RECITERS.get(reciter_key, RECITERS['dossari'])[1]}\n"
        f"• المؤثرات: تظليل الكلمات بالذهب + الغلاف التلقائي المدمج 📸\n\n"
        f"⏳ انتظر حوالي 40 ثانية...",
        parse_mode="HTML"
    )

    try:
        tag = f"ai_{update.effective_user.id}_{int(time.time())}"
        vid_path, cov_path, s_name, r_name = await asyncio.to_thread(
            produce_video_pipeline, surah_num, start_a, end_a, reciter_key, tag
        )

        with open(vid_path, "rb") as vf, open(cov_path, "rb") as cf:
            caption = (
                f"🕊️ <b>سورة {s_name} ({start_a}-{end_a})</b>\n"
                f"🎙️ بصوت القارئ: {r_name}\n\n"
                f"✨ تم إنتاج المقطع ودمج الغلاف وتظليل الذهب بالكامل لك عبر الذكاء الاصطناعي 🤍"
            )
            await update.message.reply_video(video=vf, thumbnail=cf, caption=caption, parse_mode="HTML")

        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء المونتاج: {e}")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"أهلاً بك يا {update.effective_user.first_name} في <b>بوت القرآن الكريم فائق الذكاء (AI Engine)</b> 🌿\n\n"
        "💡 <b>اكتب لي أي شيء تريده بالعامية أو الفصحى وسأفهمك فوراً!</b>\n"
        "أمثلة:\n"
        "• <i>«حاسس بضيق ومحتاج آية تريح قلبي»</i>\n"
        "• <i>«اعملي فيديو بصوت مشاري العفاسي عن الرزق»</i>\n"
        "• <i>«نزل سورة الملك قبل ما أنام»</i>\n"
        "• <i>«عايز تلاوة مؤثرة للمنشاوي»</i>\n\n"
        "وسأقوم باختيار الآيات وتوليد الفيديو بغلافه الرسمي لك فوراً 🤍"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

def main():
    if not BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN مفقود!", flush=True)
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    # استقبال أي كلام عشوائي وتمريره للذكاء الاصطناعي
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_message))

    print("🚀 تم تشغيل البوت المربوط بالذكاء الاصطناعي 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

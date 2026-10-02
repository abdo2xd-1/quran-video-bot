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

# ترقيع توافق Pillow مع MoviePy 1.0.3
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None).LANCZOS if hasattr(PIL.Image, 'Resampling') else None)

from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

# بيانات ومسارات القراء المعتمدة
RECITERS = {
    "dossari": ("Yasser_Ad-Dussary_128kbps", "ياسر الدوسري"),
    "qatami": ("Nasser_Alqatami_128kbps", "ناصر القطامي"),
    "abbad": ("Fares_Abbad_64kbps", "فارس عباد"),
    "muaiqly": ("Maher_AlMuaiqly_64kbps", "ماهر المعيقلي"),
    "alafasy": ("Alafasy_128kbps", "مشاري العفاسي"),
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

def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']:
        text = text.replace(s, '')
    return text.strip()

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

# ----------------- 1. محرك الذكاء الاصطناعي (Gemini Router) -----------------
def ask_gemini_brain(user_prompt):
    """تحليل طلب المستخدم وتحديد ما إذا كان قرآناً أو محتوى عاماً وصياغة السيناريو"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    system_instruction = (
        "أنت العقل الموجه لروبوت إنتاج فيديوهات ريلز وشورتس احترافية بالكامل. "
        "افحص رسالة المستخدم وحدد النوع:\n"
        "1. إذا كان يطلب قرآناً أو آية أو سورة (مثال: سورة الكهف، تلاوة، آيات عن الصبر)، اجعل contentType = 'quran'. "
        "حدد رقم السورة (surah)، آية البداية (start)، آية النهاية (end)، والقارئ (dossari, alafasy, qatami, abbad, minshawi).\n"
        "2. إذا كان يطلب أي موضوع عام (تاريخ، فضاء، تحفيز، علم نفس، حقائق، معلومات، قصة، إلخ)، اجعل contentType = 'general'. "
        "اكتب له نص إلقاء صوتي كامل باللهجة الفصحى السلسة والمشوقة (مدته حوالي 25-35 ثانية)، "
        "وقسّمه إلى 3 أو 4 جمل قصيرة (sentences)، وضع لكل جملة كلمات بحث سينمائية عمودية بالإنجليزية لـ Pexels (pexels_query).\n"
        "أرجع الرد بصيغة JSON حصراً بهذا الهيكل الصارم دون أي شرح:\n"
        "{\n"
        "  \"contentType\": \"quran\" أو \"general\",\n"
        "  \"reply_message\": \"رسالة لطيفة للمستخدم تخبره بما سيتم إنتاجه\",\n"
        "  \"title\": \"عنوان جذاب للمقطع أقل من 60 حرف\",\n"
        "  \"badge\": \"عبارة شريط علوي مختصرة\",\n"
        "  \"surah\": 18,\n"
        "  \"start\": 1,\n"
        "  \"end\": 10,\n"
        "  \"reciter\": \"dossari\",\n"
        "  \"sentences\": [\n"
        "    {\"text\": \"الجملة الأولى\", \"search\": \"cinematic space stars vertical\"},\n"
        "    {\"text\": \"الجملة الثانية\", \"search\": \"galaxy nebula drone vertical\"}\n"
        "  ]\n"
        "}"
    )

    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nطلب المستخدم: {user_prompt}"}]}],
        "generationConfig": {"temperature": 0.3}
    }

    try:
        res = requests.post(url, json=payload, timeout=20).json()
        raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        print(f"Gemini API Error: {e}", flush=True)
        return {
            "contentType": "general",
            "reply_message": "سأصنع لك مقطعاً مميزاً الآن 🤍",
            "title": "معلومة قد تغير تفكيرك اليوم 🌿",
            "badge": "💡 معلومة وإلهام",
            "sentences": [
                {"text": "النجاح لا يأتي بالصدفة، بل هو نتاج خطوات صغيرة مستمرة كل يوم.", "search": "success motivation running mountain vertical"},
                {"text": "لا تنتظر الفرصة المثالية، بل اصنع فرصتك بيدك الآن.", "search": "sunrise cinematic drone mountains vertical"}
            ]
        }

# ----------------- 2. توليد الصوت بالذكاء الاصطناعي (Edge-TTS) -----------------
async def generate_speech_audio(text, output_audio_path):
    """توليد تعليق صوتي فائق الواقعية عبر محرك Edge-TTS"""
    voice = "ar-EG-ShakirNeural" # صوت مصري/عربي فخم وواضح
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--text", text,
        "--write-media", output_audio_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await proc.communicate()
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 3000:
            return True
    except Exception:
        pass

    # بديل احتياطي باستخدام gTTS
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='ar', slow=False)
        tts.save(output_audio_path)
        return True
    except Exception:
        return False

# ----------------- 3. رسم بطاقات النصوص والأغلفة -----------------
def render_text_frame(text, badge, index, font_b64):
    chrome_bin = get_chrome()
    words = text.split()
    font_size = 64 if len(words) <= 8 else (50 if len(words) <= 15 else 42)

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriCustom'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }}
  .badge {{ position: absolute; top: 190px; background: rgba(10,14,20,0.65); border: 1px solid rgba(212,175,55,0.45); color: #fff; font-family: 'AmiriCustom'; font-size: 26px; padding: 10px 28px; border-radius: 30px; }}
  .content {{ direction: rtl; text-align: center; font-family: 'AmiriCustom'; font-size: {font_size}px; font-weight: bold; line-height: 1.85; max-width: 930px; color: #FFFFFF; text-shadow: 0 0 14px rgba(0,0,0,0.95), 0 4px 20px rgba(0,0,0,0.9); }}
  .watermark {{ position: absolute; bottom: 110px; left: 50%; transform: translateX(-50%); font-family: 'AmiriCustom'; font-size: 24px; color: rgba(255,255,255,0.45); direction: ltr; }}
</style></head>
<body>
  <div class="badge">{badge}</div>
  <div class="content">{text}</div>
  <div class="watermark">@content_ai</div>
</body></html>"""

    h_path = f"tmp_txt_{index}.html"
    p_path = f"frame_txt_{index}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def generate_custom_cover(title_text, badge_text, font_b64, output_path="auto_cover.jpg"):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriCustom'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; position: relative; }}
  .grid-box {{ width: 1080px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; text-align: center; }}
  .outer-circle {{ position: absolute; width: 780px; height: 780px; border-radius: 50%; border: 2px solid rgba(212, 175, 55, 0.45); box-shadow: 0 0 35px rgba(212, 175, 55, 0.15); }}
  .badge {{ font-family: 'AmiriCustom', sans-serif; font-size: 26px; color: #e6edf3; background: rgba(0, 0, 0, 0.4); padding: 8px 24px; border-radius: 20px; border: 1px solid rgba(212, 175, 55, 0.3); margin-bottom: 25px; z-index: 2; }}
  .title {{ font-family: 'AmiriCustom', serif; font-size: 68px; font-weight: bold; color: #D4AF37; line-height: 1.35; max-width: 860px; text-shadow: 0 0 20px rgba(212, 175, 55, 0.8); z-index: 2; }}
</style></head>
<body>
  <div class="grid-box">
    <div class="outer-circle"></div>
    <div class="badge">{badge_text}</div>
    <div class="title">{title_text}</div>
  </div>
</body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(output_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return output_path

# ----------------- 4. مونتاج المحتوى العام بالذكاء الاصطناعي -----------------
async def produce_general_ai_video(ai_data, tag):
    font_b64 = get_font_base64()
    sentences = ai_data.get("sentences", [])
    badge = ai_data.get("badge", "💡 معلومات وإلهام")
    
    audio_clips = []
    text_clips = []
    curr_time = 0.0

    # 1. توليد الصوت لكل جملة مع النصوص المتزامنة
    for idx, s in enumerate(sentences):
        aud_file = f"aud_{tag}_{idx}.mp3"
        await generate_speech_audio(s["text"], aud_file)
        
        ac = AudioFileClip(aud_file)
        audio_clips.append(ac)
        
        frame_img = render_text_frame(s["text"], badge, idx, font_b64)
        tc = ImageClip(frame_img).set_start(curr_time).set_duration(ac.duration).set_position(("center", "center"))
        text_clips.append(tc)
        curr_time += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    total_dur = curr_time + 1.0

    # 2. جلب فيديو خلفية من Pexels ملائم للموضوع
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    search_q = sentences[0].get("search", "cinematic nature vertical 4k")
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get(f"https://api.pexels.com/videos/search?query={search_q}&orientation=portrait&per_page=6", headers=headers, timeout=15).json()
    
    videos = res.get("videos", [])
    if videos:
        best_v = sorted(random.choice(videos)["video_files"], key=lambda x: x.get("width", 0))[-1]["link"]
    else:
        best_v = "https://cdn.pixabay.com/video/2020/05/25/40149-425265565_tiny.mp4"

    bg_file = f"bg_{tag}.mp4"
    with open(bg_file, "wb") as f:
        f.write(requests.get(best_v, timeout=35).content)

    bg_clip = VideoFileClip(bg_file)
    bg_clip = (bg_clip.loop(duration=total_dur) if bg_clip.duration < total_dur else bg_clip.subclip(0, total_dur)).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.35).set_duration(total_dur)

    main_video = CompositeVideoClip([bg_clip, dim] + text_clips).set_audio(final_audio)

    # 3. إعداد ودمج الغلاف التلقائي
    cover_file = f"cover_{tag}.jpg"
    generate_custom_cover(ai_data.get("title", "فيديو اليوم"), badge, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.12).resize((1080, 1920))

    temp_joined = f"temp_{tag}.mp4"
    joined_video = concatenate_videoclips([cover_clip, main_video])
    joined_video.write_videofile(temp_joined, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")

    out_file = f"final_{tag}.mp4"
    embed_cmd = ["ffmpeg", "-y", "-i", temp_joined, "-i", cover_file, "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic", out_file]
    try:
        subprocess.run(embed_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        out_file = temp_joined

    return out_file, cover_file

# ----------------- 5. مونتاج القرآن الكريم -----------------
def download_quran_audio(surah_num, ayah_num, rec_id, out_file):
    surah_str = f"{surah_num:03d}"
    ayah_str = f"{ayah_num:03d}"
    sources = [
        f"https://everyayah.com/data/{rec_id}/{surah_str}{ayah_str}.mp3",
        f"https://everyayah.com/data/Yasser_Ad-Dussary_128kbps/{surah_str}{ayah_str}.mp3",
        f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3"
    ]
    for url in sources:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 4000:
                with open(out_file, "wb") as f:
                    f.write(r.content)
                return True
        except Exception:
            continue
    return False

def produce_quran_video(surah_num, start_a, end_a, reciter_key, tag):
    rec_id, rec_name = RECITERS.get(reciter_key, RECITERS["dossari"])
    meta = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}", timeout=15).json()
    surah_name = meta.get("data", {}).get("name", f"سورة {surah_num}").replace("سورة ", "")

    ayahs = []
    for a in range(start_a, end_a + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic(t_res.get("data", {}).get("text", ""))
        if a == 1 and surah_num != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        aud_file = f"aud_q_{tag}_{a}.mp3"
        download_quran_audio(surah_num, a, rec_id, aud_file)
        ayahs.append({"text": txt, "audio": aud_file})

    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=switzerland+mountains+drone+vertical&orientation=portrait&per_page=6", headers=headers, timeout=15).json()
    v_files = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))
    bg_file = f"bg_q_{tag}.mp4"
    with open(bg_file, "wb") as f:
        f.write(requests.get(v_files[-1]["link"], timeout=35).content)

    font_b64 = get_font_base64()
    audio_clips, text_clips = [], []
    curr_t = 0.0

    for idx, ay in enumerate(ayahs):
        ac = AudioFileClip(ay["audio"])
        audio_clips.append(ac)
        frame_img = render_text_frame(ay["text"], f"سورة {surah_name}", idx, font_b64)
        tc = ImageClip(frame_img).set_start(curr_t).set_duration(ac.duration).set_position(("center", "center"))
        text_clips.append(tc)
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 1.0

    bg = VideoFileClip(bg_file)
    bg = (bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.22).set_duration(tot_dur)

    main_vid = CompositeVideoClip([bg, dim] + text_clips).set_audio(final_audio)

    cover_file = f"cover_q_{tag}.jpg"
    generate_custom_cover(f"سُورَةُ {surah_name}", f"بصوت القارئ {rec_name}", font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.12).resize((1080, 1920))

    temp_joined = f"temp_q_{tag}.mp4"
    joined_video = concatenate_videoclips([cover_clip, main_vid])
    joined_video.write_videofile(temp_joined, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")

    out_file = f"final_q_{tag}.mp4"
    embed_cmd = ["ffmpeg", "-y", "-i", temp_joined, "-i", cover_file, "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic", out_file]
    try:
        subprocess.run(embed_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        out_file = temp_joined

    return out_file, cover_file, surah_name, rec_name

# ----------------- 6. معالج رسائل تليجرام الموحد -----------------
async def handle_any_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text.strip()
    status_msg = await update.message.reply_text("🤖 <i>جاري تحليل فكرتك وصياغة السيناريو بالذكاء الاصطناعي...</i>", parse_mode="HTML")

    ai_data = await asyncio.to_thread(ask_gemini_brain, user_prompt)
    content_type = ai_data.get("contentType", "general")
    reply_note = ai_data.get("reply_message", "جاري تحضير الفيديو 🎬")

    tag = f"usr_{update.effective_user.id}_{int(time.time())}"

    if content_type == "quran":
        surah_num = ai_data.get("surah", 18)
        start_a = ai_data.get("start", 1)
        end_a = ai_data.get("end", 10)
        reciter = ai_data.get("reciter", "dossari")
        
        await status_msg.edit_text(
            f"🕌 <b>{reply_note}</b>\n\n"
            f"📖 <b>المقطع القرآني:</b> سورة رقم {surah_num} ({start_a}-{end_a})\n"
            f"🎙️️ <b>القارئ:</b> {RECITERS.get(reciter, RECITERS['dossari'])[1]}\n\n"
            f"⏳ جاري تجهيز المقطع والغلاف التلقائي...",
            parse_mode="HTML"
        )
        try:
            vid_path, cov_path, s_name, r_name = await asyncio.to_thread(
                produce_quran_video, surah_num, start_a, end_a, reciter, tag
            )
            with open(vid_path, "rb") as vf, open(cov_path, "rb") as cf:
                caption = f"🤍 <b>سورة {s_name} ({start_a}-{end_a})</b>\n🎙️ بصوت القارئ: {r_name} 🌿"
                await update.message.reply_video(video=vf, thumbnail=cf, caption=caption, parse_mode="HTML")
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ حدث خطأ أثناء المونتاج: {e}")

    else:
        title = ai_data.get("title", "فيديو اليوم")
        await status_msg.edit_text(
            f"✨ <b>{reply_note}</b>\n\n"
            f"🎬 <b>العنوان:</b> {title}\n"
            f"🎙️ <b>التعليق الصوتي:</b> جاري توليد الصوت الواقعي (Edge-TTS)\n"
            f"🎞️ <b>المشاهد:</b> جاري اختيار اللقطات السينمائية من Pexels\n\n"
            f"⏳ انتظر حوالي 35 ثانية...",
            parse_mode="HTML"
        )
        try:
            vid_path, cov_path = await produce_general_ai_video(ai_data, tag)
            with open(vid_path, "rb") as vf, open(cov_path, "rb") as cf:
                caption = f"✨ <b>{title}</b>\n\nتم إنتاج السيناريو والصوت والمونتاج بالكامل بواسطة الذكاء الاصطناعي 🚀"
                await update.message.reply_video(video=vf, thumbnail=cf, caption=caption, parse_mode="HTML")
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ حدث خطأ أثناء الإنتاج: {e}")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"مرحباً بك يا {update.effective_user.first_name} في <b>منشئ الفيديوهات الشامل بالذكاء الاصطناعي</b> 🎬\n\n"
        "💡 <b>أصبح بإمكانك طلب أي فيديو تريده على الإطلاق!</b>\n\n"
        "🔹 <b>مواضيع عامة:</b>\n"
        "• <i>«اعملي فيديو عن أسرار الثقوب السوداء في الفضاء»</i>\n"
        "• <i>«فيديو تحفيزي عن الانضباط وتحقيق الأحلام»</i>\n"
        "• <i>«حقائق نفسية مدهشة عن العقل البشري»</i>\n\n"
        "🔹 <b>مقاطع قرآنية:</b>\n"
        "• <i>«سورة الكهف بصوت ياسر الدوسري»</i>\n"
        "• <i>«آيات تريح القلب إذا ضاقت الدنيا»</i>\n\n"
        "سيتولى Gemini كتابة السيناريو واختيار المشاهد وتوليد الصوت والمونتاج والغلاف فوراً 🚀"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

def main():
    if not BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN مفقود!", flush=True)
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_prompt))

    print("🚀 تم تشغيل البوت الشامل بالذكاء الاصطناعي 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

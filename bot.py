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

# تقسيم سورة الكهف إلى 10 أجزاء شورتس متناسقة سياقياً
KAHF_PARTS_SPLIT = [
    {"part": 1, "start": 1, "end": 10, "theme": "العصمة من فتن الدجال"},
    {"part": 2, "start": 11, "end": 16, "theme": "دخول الكهف وثبات الفتية"},
    {"part": 3, "start": 17, "end": 22, "theme": "نومهم في الكهف وقدرة الله"},
    {"part": 4, "start": 23, "end": 31, "theme": "ولا تقولن لشيء إني فاعل ذلك غدا"},
    {"part": 5, "start": 32, "end": 44, "theme": "قصة صاحب الجنتين"},
    {"part": 6, "start": 45, "end": 53, "theme": "مثل الحياة الدنيا ومصير المجرمين"},
    {"part": 7, "start": 54, "end": 64, "theme": "رحلة موسى عليه السلام وفتاه"},
    {"part": 8, "start": 65, "end": 82, "theme": "موسى والعبد الصالح الخضر"},
    {"part": 9, "start": 83, "end": 98, "theme": "قصة ذي القرنين ويأجوج ومأجوج"},
    {"part": 10, "start": 99, "end": 110, "theme": "نفخ الصور وجنات الفردوس"}
]

RECITERS_MAP = {
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

def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']:
        text = text.replace(s, '')
    return text.strip()

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

# درع كسر البصمة الصوتية وحقوق الملكية
def apply_anti_copyright_audio(input_audio, output_audio):
    audio_filter = (
        "aresample=44100,"
        "asetrate=44100*1.018,"
        "atempo=0.982,"
        "aecho=0.8:0.75:32:0.22,"
        "equalizer=f=1100:width_type=q:w=1:g=1.8"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", input_audio,
        "-af", audio_filter,
        "-b:a", "192k",
        output_audio
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_audio

def download_ayah_safe(surah_num, ayah_num, rec_id, out_file):
    surah_str = f"{surah_num:03d}"
    ayah_str = f"{ayah_num:03d}"
    raw_tmp = f"raw_{surah_str}_{ayah_str}.mp3"

    urls = [
        f"https://everyayah.com/data/{rec_id}/{surah_str}{ayah_str}.mp3",
        f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3",
        f"https://everyayah.com/data/Yasser_Ad-Dussary_128kbps/{surah_str}{ayah_str}.mp3"
    ]
    downloaded = False
    for u in urls:
        try:
            r = requests.get(u, timeout=20)
            if r.status_code == 200 and len(r.content) > 4000 and not r.content.startswith(b"<!DOCTYPE"):
                with open(raw_tmp, "wb") as f:
                    f.write(r.content)
                downloaded = True
                break
        except Exception:
            continue

    if downloaded:
        try:
            apply_anti_copyright_audio(raw_tmp, out_file)
            if os.path.exists(raw_tmp):
                os.remove(raw_tmp)
            return True
        except Exception:
            if os.path.exists(raw_tmp):
                os.rename(raw_tmp, out_file)
                return True
    return False

def render_quran_frame(words, active_idx, badge_text, font_b64):
    chrome_bin = get_chrome()
    words_html = []
    for i, w in enumerate(words):
        if i == active_idx:
            words_html.append(f'<span style="color:#D4AF37; transform:scale(1.08); text-shadow:0 0 16px rgba(212,175,55,0.95);">{w}</span>')
        else:
            words_html.append(f'<span style="color:#FFFFFF; text-shadow:0 0 10px rgba(0,0,0,0.95);">{w}</span>')

    full_verse = " ".join(words_html)
    font_size = 68 if len(words) <= 7 else (52 if len(words) <= 14 else 42)

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }}
  .badge {{ position: absolute; top: 190px; background: rgba(10,14,20,0.7); border: 1px solid rgba(212,175,55,0.45); color: #fff; font-family: 'Amiri'; font-size: 26px; padding: 10px 28px; border-radius: 30px; }}
  .ayah {{ direction: rtl; text-align: center; font-family: 'Amiri'; font-size: {font_size}px; font-weight: bold; line-height: 1.95; max-width: 930px; margin: auto 0; }}
  .watermark {{ position: absolute; bottom: 110px; left: 50%; transform: translateX(-50%); font-family: 'Amiri'; font-size: 24px; color: rgba(255,255,255,0.45); direction: ltr; }}
</style></head>
<body>
  <div class="badge">🎧 {badge_text} 🌿</div>
  <div class="ayah">{full_verse}</div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path, p_path = f"tmp_{active_idx}.html", f"frame_{active_idx}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def generate_cover_file(surah_name, part_num, total_parts, reciter_name, font_b64, out_cover):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; position: relative; }}
  .box {{ width: 1080px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
  .circle {{ position: absolute; width: 780px; height: 780px; border-radius: 50%; border: 2px solid rgba(212, 175, 55, 0.45); }}
  .badge {{ font-family: 'Amiri'; font-size: 26px; color: #fff; background: rgba(0,0,0,0.5); padding: 8px 24px; border-radius: 20px; border: 1px solid rgba(212,175,55,0.3); margin-bottom: 20px; z-index: 2; }}
  .title {{ font-family: 'Amiri'; font-size: 82px; font-weight: bold; color: #D4AF37; margin-bottom: 15px; z-index: 2; text-shadow: 0 0 20px rgba(212,175,55,0.8); }}
  .reciter {{ font-family: 'Amiri'; font-size: 38px; color: #fff; z-index: 2; margin-bottom: 15px; }}
  .part {{ font-family: 'Amiri'; font-size: 28px; color: rgba(212,175,55,0.9); z-index: 2; }}
</style></head>
<body><div class="box">
  <div class="circle"></div>
  <div class="badge">🕌 نور ما بين الجمعتين 🌿</div>
  <div class="title">سُورَةُ {surah_name}</div>
  <div class="reciter">بصوت القارئ {reciter_name}</div>
  <div class="part">الجزء ({part_num} من {total_parts}) • تظليل الذهب</div>
</div></body></html>"""

    h_path = f"tmp_cov_{part_num}.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", f"--screenshot={os.path.abspath(out_cover)}", f"file://{os.path.abspath(h_path)}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return out_cover

def build_single_short(surah_num, surah_name, start_a, end_a, part_num, total_parts, reciter_key, tag):
    rec_id, rec_name = RECITERS_MAP.get(reciter_key, RECITERS_MAP["dossari"])
    badge_label = f"سورة {surah_name} • الجزء ({part_num}/{total_parts})"

    ayahs = []
    font_b64 = get_font_base64()
    for a in range(start_a, end_a + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic(t_res.get("data", {}).get("text", ""))
        if a == 1 and surah_num != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        aud_file = f"aud_{tag}_{part_num}_{a}.mp3"
        download_ayah_safe(surah_num, a, rec_id, aud_file)
        ayahs.append({"text": txt, "audio": aud_file})

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
            frame_img = render_quran_frame(words, idx, badge_label, font_b64)
            text_clips.append(ImageClip(frame_img).set_start(w_start).set_duration(w_dur).set_position(("center", "center")))
            w_start += w_dur
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 0.8

    # جلب فيديو طبيعي
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=scenic+mountains+drone+vertical&orientation=portrait&per_page=8", headers=headers, timeout=15).json()
    v_files = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))
    bg_file = f"bg_{tag}_{part_num}.mp4"
    with open(bg_file, "wb") as f:
        f.write(requests.get(v_files[-1]["link"], timeout=35).content)

    # تكبير خفيف بنسبة 4% لكسر البصمة البصرية
    bg = VideoFileClip(bg_file)
    bg = (bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)).resize(1.04).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(10, 15, 20)).set_opacity(0.28).set_duration(tot_dur)

    main_video = CompositeVideoClip([bg, dim] + text_clips).set_audio(final_audio)

    cover_file = f"cover_{tag}_{part_num}.jpg"
    generate_cover_file(surah_name, part_num, total_parts, rec_name, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.12).resize((1080, 1920))

    # ضبط معدل البت ديناميكياً لضمان بقاء الحجم أقل من 38MB
    max_bits = 38 * 1024 * 1024 * 8
    target_k = int(max_bits / max(tot_dur, 1)) // 1000
    safe_bitrate = f"{max(800, min(target_k, 2000))}k"

    temp_joined = f"temp_{tag}_{part_num}.mp4"
    joined = concatenate_videoclips([cover_clip, main_video])
    joined.write_videofile(temp_joined, fps=24, codec="libx264", audio_codec="aac", bitrate=safe_bitrate, threads=4, preset="ultrafast")

    out_file = f"short_{surah_name}_part{part_num}.mp4"
    embed_cmd = ["ffmpeg", "-y", "-i", temp_joined, "-i", cover_file, "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic", out_file]
    try:
        subprocess.run(embed_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        out_file = temp_joined

    # فحص أخير: لو تخطى 45MB يتم ضغطه فوراً
    if os.path.exists(out_file) and os.path.getsize(out_file) > 45 * 1024 * 1024:
        compressed_out = f"cmp_{out_file}"
        c_cmd = ["ffmpeg", "-y", "-i", out_file, "-vcodec", "libx264", "-crf", "28", "-b:a", "128k", compressed_out]
        try:
            subprocess.run(c_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(compressed_out):
                os.replace(compressed_out, out_file)
        except Exception:
            pass

    # تنظيف الملفات المؤقتة
    for ay in ayahs:
        if os.path.exists(ay["audio"]): os.remove(ay["audio"])
    if os.path.exists(bg_file): os.remove(bg_file)
    if os.path.exists(temp_joined) and temp_joined != out_file: os.remove(temp_joined)

    return out_file, cover_file, rec_name

# ----------------- معالج الرسائل -----------------
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip().lower()
    tag = f"{update.effective_user.id}_{int(time.time())}"

    if "الكهف" in user_text and any(k in user_text for k in ["قسم", "شورت", "شورتس", "اجزاء", "أجزاء", "كلها"]):
        status_msg = await update.message.reply_text(
            "🚀 <b>تم تفعيل مُقسّم سورة الكهف الشامل (مع حماية الحجم 🛡️)!</b>\n\n"
            "جاري إنتاج الـ 10 أجزاء شورتس بضغط ذكي لتفادي رفض تيليجرام...\n"
            "⏳ سأرسل لك كل جزء فور اكتماله مباشرة!",
            parse_mode="HTML"
        )

        for item in KAHF_PARTS_SPLIT:
            p_num = item["part"]
            try:
                vid_path, cov_path, r_name = await asyncio.to_thread(
                    build_single_short, 18, "الكهف", item["start"], item["end"], p_num, 10, "dossari", tag
                )
                caption = (
                    f"🕌 <b>سورة الكهف • الجزء ({p_num} من 10)</b>\n"
                    f"📖 الآيات: ({item['start']} - {item['end']})\n"
                    f"🌿 الموضوع: {item['theme']}\n"
                    f"🎙️ بصوت القارئ: {r_name}\n\n"
                    f"#سورة_الكهف #يوم_الجمعة #جمعة_مباركة #shorts #reels"
                )
                with open(vid_path, "rb") as vf, open(cov_path, "rb") as cf:
                    await update.message.reply_video(
                        video=vf, 
                        thumbnail=cf, 
                        caption=caption, 
                        parse_mode="HTML",
                        read_timeout=300,
                        write_timeout=300
                    )

                if os.path.exists(vid_path): os.remove(vid_path)
                if os.path.exists(cov_path): os.remove(cov_path)
                await asyncio.sleep(4)

            except Exception as e:
                await update.message.reply_text(f"⚠️ تعذر إرسال الجزء {p_num}: {e}")

        await status_msg.edit_text("✅ <b>اكتمل إنتاج وإرسال جميع أجزاء سورة الكهف (10 أجزاء) بنجاح تام وبأحجام متوافقة!</b> 🌿", parse_mode="HTML")
        return

    # طلب جزء محدد فقط
    if "الكهف" in user_text:
        item = KAHF_PARTS_SPLIT[0]
        status_msg = await update.message.reply_text("⏳ جاري إنتاج مقطع شورتس لسورة الكهف (الجزء 1)...")
        vid_path, cov_path, r_name = await asyncio.to_thread(
            build_single_short, 18, "الكهف", item["start"], item["end"], 1, 10, "dossari", tag
        )
        with open(vid_path, "rb") as vf, open(cov_path, "rb") as cf:
            await update.message.reply_video(video=vf, thumbnail=cf, caption=f"سورة الكهف - الجزء 1 من 10 بصوت {r_name} 🌿", parse_mode="HTML")
        await status_msg.delete()
        return

    await update.message.reply_text("أهلاً بك! اكتب: <b>«قسم سورة الكهف كلها شورتس»</b> وسأقوم بمونتاج وإرسال أجزاء السورة كاملة تباعاً 🤍", parse_mode="HTML")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"أهلاً بك يا {update.effective_user.first_name} في <b>بوت تقسيم ومونتاج الشورتس الذكي</b> 🎬\n\n"
        "✨ <b>الأمر السحري:</b>\n"
        "اكتب: <code>قسم سورة الكهف كلها شورتس</code>\n"
        "وسيقوم البوت تلقائياً بإنتاج وإرسال الـ 10 أجزاء بدون أي أخطاء في الحجم!"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

def main():
    if not BOT_TOKEN:
        print("خطأ: TELEGRAM_BOT_TOKEN مفقود!", flush=True)
        sys.exit(1)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(300)
        .write_timeout(300)
        .connect_timeout(60)
        .build()
    )
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))

    print("🚀 تم تشغيل محرك تقسيم الشورتس مع الحماية من الحجم الزائد 24/7...", flush=True)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

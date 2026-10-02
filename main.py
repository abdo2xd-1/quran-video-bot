import os
import sys
import json
import time
import uuid
import base64
import random
import shutil
import datetime
import subprocess
import requests

# إصلاح توافق MoviePy 1.0.3 مع إصدارات Pillow الحديثة
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)

# ----------------- مقاطع شورتس سورة الكهف ليوم الجمعة -----------------
KAHF_SHORTS_SERIES = [
    {
        "surah": 18, "start": 1, "end": 10, "name": "الكهف",
        "badge": "سورة الكهف • العصمة من الفتن 🌿",
        "hook": "أول 10 آيات من سورة الكهف.. نور ما بين الجمعتين 🤍",
        "title": "سورة الكهف (1-10) نور ما بين الجمعتين 🤍 #shorts"
    },
    {
        "surah": 18, "start": 13, "end": 17, "name": "الكهف",
        "badge": "قصة أصحاب الكهف وثبات الإيمان 🕊️",
        "hook": "إنهم فتية آمنوا بربهم وزدناهم هدى.. سورة الكهف 🌿",
        "title": "قصة أصحاب الكهف | جمعة مباركة وطيبة 🤍 #shorts"
    },
    {
        "surah": 18, "start": 45, "end": 49, "name": "الكهف",
        "badge": "واضرب لهم مثل الحياة الدنيا 🌧️",
        "hook": "المال والبنون زينة الحياة الدنيا.. تلاوة خاشعة 🤍",
        "title": "مثل الحياة الدنيا | سورة الكهف يوم الجمعة 🌿 #shorts"
    },
    {
        "surah": 18, "start": 65, "end": 70, "name": "الكهف",
        "badge": "موسى والخضر وحكمة الأقدار 🕊️",
        "hook": "فوجدا عبداً من عبادنا آتيناه رحمة من عندنا.. سورة الكهف 🤍",
        "title": "موسى والخضر | سورة الكهف نور لقلبك 🤍 #shorts"
    },
    {
        "surah": 18, "start": 107, "end": 110, "name": "الكهف",
        "badge": "ختام سورة الكهف وجنات الفردوس 🌿",
        "hook": "إن الذين آمنوا وعملوا الصالحات كانت لهم جنات الفردوس نزلاً 🤍",
        "title": "ختام سورة الكهف | نور ما بين الجمعتين 🕊️ #shorts"
    }
]

# قائمة السور للأيام العادية (السبت إلى الخميس)
REGULAR_PLAYLIST = [
    {"surah": 94, "start": 1, "end": 8, "name": "الشرح", "badge": "رسالة لقلبك إذا كنت حزيناً 🌿", "hook": "إذا ضاقت بك الدنيا.. استمع لرسالة الله 🤍"},
    {"surah": 65, "start": 2, "end": 3, "name": "الطلاق", "badge": "إذا كنت قلقاً من الرزق 🕊️", "hook": "اطمئن على رزقك.. الأمر كله بيد الله 🌿"},
    {"surah": 93, "start": 1, "end": 5, "name": "الضحى", "badge": "أمل يتجدد ومغفرة من الله 🤍", "hook": "ما ودعك ربك وما قلى.. سكينة لقلبك 🌿"},
    {"surah": 67, "start": 1, "end": 4, "name": "الملك", "badge": "أمان لقلبك وحصن من العذاب 🌙", "hook": "تلاوة هادئة لراحة البال والسكينة 🕊️"},
    {"surah": 92, "start": 1, "end": 7, "name": "الليل", "badge": "والليل إذا يغشى والنهار إذا تجلى 🌿", "hook": "فسنيسره لليسرى.. تلاوة خاشعة 🤍"},
    {"surah": 1,  "start": 1, "end": 7, "name": "الفاتحة", "badge": "أم الكتاب والشفاء التام 🤍", "hook": "الفاتحة تريح قلبك وتفتح لك أبواب الخير 🕊️"}
]

RECITERS_POOL = [
    {"id": "Dussary_128kbps", "name": "ياسر الدوسري"},
    {"id": "Nasser_Alqatami_128kbps", "name": "ناصر القطامي"},
    {"id": "Fares_Abbad_64kbps", "name": "فارس عباد"},
    {"id": "MaherAlMuaiqly128kbps", "name": "ماهر المعيقلي"},
    {"id": "Alafasy_128kbps", "name": "مشاري العفاسي"}
]

PINNED_COMMENTS_FRIDAY = [
    "جمعة مباركة وطيبة 🌿 صلوا على الحبيب المصطفى ﷺ واقرؤوا سورة الكهف نورا لكم بين الجمعتين 🤍",
    "لا تنسَ قراءة سورة الكهف والصلاة على النبي ﷺ في هذا اليوم المبارك 🕊️ اكتب شيئاً تؤجر عليه 🤍",
    "اللهم في يوم الجمعة اجعلنا من أهل الفردوس الأعلى واغفر لنا ولوالدينا ولجميع المسلمين 🤲"
]

FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

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

def clean_arabic_text(text):
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

def render_ayah_card(text, index, font_b64, badge="سورة الكهف"):
    chrome_bin = get_chrome()
    words = text.split()
    font_size = 65 if len(words) <= 7 else (54 if len(words) <= 14 else 44)

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }}
  .badge {{ position: absolute; top: 190px; background: rgba(10,14,20,0.65); border: 1px solid rgba(212,175,55,0.45); color: #fff; font-family: 'AmiriQuran'; font-size: 26px; padding: 10px 28px; border-radius: 30px; }}
  .ayah {{ direction: rtl; text-align: center; font-family: 'AmiriQuran'; font-size: {font_size}px; font-weight: bold; line-height: 1.95; max-width: 920px; color: #FFFFFF; text-shadow: 0 0 12px rgba(0,0,0,0.95), 0 4px 18px rgba(0,0,0,0.9); }}
  .watermark {{ position: absolute; bottom: 110px; left: 50%; transform: translateX(-50%); font-family: 'AmiriQuran'; font-size: 24px; color: rgba(255,255,255,0.45); direction: ltr; }}
</style></head>
<body>
  <div class="badge">🕌 {badge} 🌿</div>
  <div class="ayah">{text}</div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path = f"tmp_a_{index}.html"
    p_path = f"frame_a_{index}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path):
        os.remove(h_path)
    return p_path

def generate_cover(surah_title, reciter_name, is_full=False, output_path="cover.jpg"):
    chrome_bin = get_chrome()
    font_b64 = get_font_base64()
    sub_text = "سُورَةُ الْكَهْفِ كَامِلَةً" if is_full else "نُورٌ مَا بَيْنَ الْجُمُعَتَيْنِ"

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; position: relative; }}
  .grid-box {{ width: 1080px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; text-align: center; }}
  .outer-circle {{ position: absolute; width: 780px; height: 780px; border-radius: 50%; border: 2px solid rgba(212, 175, 55, 0.45); box-shadow: 0 0 35px rgba(212, 175, 55, 0.15); }}
  .badge {{ font-family: 'AmiriQuran', sans-serif; font-size: 26px; color: #e6edf3; background: rgba(0, 0, 0, 0.4); padding: 8px 24px; border-radius: 20px; border: 1px solid rgba(212, 175, 55, 0.3); margin-bottom: 25px; z-index: 2; }}
  .surah-title {{ font-family: 'AmiriQuran', serif; font-size: 82px; font-weight: bold; color: #D4AF37; line-height: 1.3; text-shadow: 0 0 20px rgba(212, 175, 55, 0.8); z-index: 2; margin-bottom: 12px; }}
  .reciter {{ font-family: 'AmiriQuran', sans-serif; font-size: 38px; color: #FFFFFF; font-weight: bold; z-index: 2; margin-bottom: 20px; }}
  .features {{ font-family: 'AmiriQuran', sans-serif; font-size: 22px; color: rgba(212, 175, 55, 0.85); z-index: 2; }}
</style></head>
<body>
  <div class="grid-box">
    <div class="outer-circle"></div>
    <div class="badge">🕌 {sub_text} 🌿</div>
    <div class="surah-title">{surah_title}</div>
    <div class="reciter">بصوت القارئ {reciter_name}</div>
    <div class="features">🎧 تلاوة خاشعة تهز القلوب • جمعة مباركة 🤍</div>
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

def build_shorts_video(item, reciter_id, reciter_name):
    font_b64 = get_font_base64()
    audio_clips, text_clips = [], []
    curr_t = 0.0

    for a in range(item["start"], item["end"] + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{item['surah']}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic_text(t_res.get("data", {}).get("text", ""))
        if a == 1 and item["surah"] != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        aud_file = f"aud_sh_{a}.mp3"
        download_audio_safe(item["surah"], a, reciter_id, aud_file)
        ac = AudioFileClip(aud_file)
        audio_clips.append(ac)

        img_path = render_ayah_card(txt, a, font_b64, item["badge"])
        text_clips.append(ImageClip(img_path).set_start(curr_t).set_duration(ac.duration).set_position(("center", "center")))
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 0.8

    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=foggy+mountains+drone+vertical&orientation=portrait&per_page=6", headers=headers, timeout=15).json()
    v_files = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))
    with open("bg_sh.mp4", "wb") as f:
        f.write(requests.get(v_files[-1]["link"], timeout=35).content)

    bg_clip = VideoFileClip("bg_sh.mp4")
    bg_clip = (bg_clip.loop(duration=tot_dur) if bg_clip.duration < tot_dur else bg_clip.subclip(0, tot_dur)).resize((1080, 1920))
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.20).set_duration(tot_dur)

    main_vid = CompositeVideoClip([bg_clip, dim] + text_clips).set_audio(final_audio)

    cover_file = generate_cover(f"سُورَةُ {item['name']}", reciter_name, is_full=False, output_path="cover_shorts.jpg")
    cover_clip = ImageClip(cover_file).set_duration(0.12).resize((1080, 1920))

    out_file = "final_shorts.mp4"
    final_video = concatenate_videoclips([cover_clip, main_vid])
    final_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")
    return out_file, cover_file

def upload_files(video_file, cover_file):
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if repo and gh_token:
        for _ in range(3):
            tag_name = f"v{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
            try:
                res = requests.post(
                    f"https://api.github.com/repos/{repo}/releases",
                    headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
                    json={"tag_name": tag_name, "name": f"Release {tag_name}", "draft": False}, timeout=20
                ).json()
                if "upload_url" in res:
                    u_url = res["upload_url"].split("{")[0]
                    with open(video_file, "rb") as vf:
                        up_res = requests.post(f"{u_url}?name=final_video.mp4", headers={"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}, data=vf, timeout=90).json()
                    return up_res.get("browser_download_url")
            except Exception:
                time.sleep(1)

    with open(video_file, "rb") as f:
        r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=90).json()
        if r.get("status") == "success":
            return r["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    return None

def post_to_buffer(video_url, yt_title, caption):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()
    if not buffer_token or not channels_raw:
        return
    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
    graphql_url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {buffer_token}", "Content-Type": "application/json"}
    mutation = """mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id } } ... on MutationError { message } } }"""

    for ch_id in channel_ids:
        post_input = {
            "channelId": ch_id, "text": caption, "mode": "shareNow", "schedulingType": "automatic",
            "assets": [{"video": {"url": video_url}}]
        }
        if ch_id in ["6aa9df26ea19ca0bde51b3c5", "6aa72b30ea19ca0bde39598b"]:
            post_input["metadata"] = {"youtube": {"title": yt_title[:65], "categoryId": "27"}}
        elif ch_id == "6aa6d1fbea19ca0bde35e91c":
            post_input["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}

        try:
            requests.post(graphql_url, headers=headers, json={"query": mutation, "variables": {"input": post_input}}, timeout=30)
        except Exception:
            pass

def notify_telegram(message, cover_file):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        if os.path.exists(cover_file):
            with open(cover_file, "rb") as pf:
                requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", data={"chat_id": chat_id, "caption": "📸 الغلاف المعتمد للفيديو 🌿"}, files={"photo": pf}, timeout=20)
    except Exception:
        pass

if __name__ == "__main__":
    now_utc = datetime.datetime.utcnow()
    is_friday = (now_utc.weekday() == 4)
    reciter = random.choice(RECITERS_POOL)

    if is_friday:
        print("🕌 ساعات الجمعة: إنتاج ونشر مقطع شورتس لسورة الكهف...", flush=True)
        item = random.choice(KAHF_SHORTS_SERIES)
        vid_file, cov_file = build_shorts_video(item, reciter["id"], reciter["name"])
        yt_title = item["title"]
        caption = (
            f"🕌 {item['hook']}\n\n"
            f"📖 سورة الكهف • نور ما بين الجمعتين\n"
            f"🎙️ القارئ: {reciter['name']}\n\n"
            f"#سورة_الكهف #يوم_الجمعة #جمعة_مباركة #الكهف #shorts"
        )
        pinned = random.choice(PINNED_COMMENTS_FRIDAY)
    else:
        print("📅 يوم عادي: إنتاج ونشر السور المتنوعة وصيدلية المشاعر...", flush=True)
        item = random.choice(REGULAR_PLAYLIST)
        vid_file, cov_file = build_shorts_video(item, reciter["id"], reciter["name"])
        yt_title = f"{item['badge'][:28]} | سورة {item['name']} 🤍 #shorts"
        caption = f"{item['hook']}\n\n📖 سورة {item['name']}\n🎙️ القارئ: {reciter['name']}\n\n#قرآن #fyp #shorts"
        pinned = "اكتب شيئاً تؤجر عليه في ميزان حسناتك 🌿 (سبحان الله، الحمد لله، لا إله إلا الله) 🤍"

    pub_url = upload_files(vid_file, cov_file)
    post_to_buffer(pub_url, yt_title, caption)

    report = (
        f"✨ <b>تم النشر بنجاح على جميع المنصات!</b>\n\n"
        f"🏷️ <b>العنوان:</b> {yt_title}\n"
        f"🎙️ <b>القارئ:</b> {reciter['name']}\n"
        f"🔗 <b>الرابط:</b> <a href='{pub_url}'>مشاهدة الفيديو</a>\n\n"
        f"📌 <b>التعليق المقترح للتثبيت:</b>\n"
        f"<code>{pinned}</code>"
    )
    notify_telegram(report, cov_file)
    print("=== اكتمل الإنتاج والنشر بنجاح ===", flush=True)

import os
import sys
import json
import base64
import random
import shutil
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips
)

# ----------------- 1. صيدلية المشاعر (Emotional Targeting Engine) -----------------
EMOTIONAL_PHARMACY = [
    {
        "emotion_id": "sadness",
        "badge": "رسالة لقلبك إذا كنت حزيناً 🌿",
        "hook": "إذا ضاقت بك الدنيا.. استمع لرسالة الله 🤍",
        "playlist": "سكينة القلوب وتفريج الهموم",
        "surah": 94, "start": 1, "end": 8, "name": "الشرح"
    },
    {
        "emotion_id": "anxiety",
        "badge": "إذا كنت قلقاً من المستقبل أو الرزق 🕊️",
        "hook": "اطمئن على رزقك.. الأمر كله بيد الله 🌿",
        "playlist": "آيات الرزق والفرج العاجل",
        "surah": 65, "start": 2, "end": 3, "name": "الطلاق"
    },
    {
        "emotion_id": "peace",
        "badge": "تلاوة تنزل السكينة على روحك 🤍",
        "hook": "أرح سمعك وفؤادك بآيات الله 🕊️",
        "playlist": "رفيق النوم والسكينة",
        "surah": 13, "start": 28, "end": 28, "name": "الرعد"
    },
    {
        "emotion_id": "hope",
        "badge": "مهما بلغت ذنوبك.. ربك غفور 🌧️",
        "hook": "أمل يتجدد مع آيات المغفرة والرحمة 🤍",
        "playlist": "أبواب التوبة والرجاء",
        "surah": 93, "start": 1, "end": 5, "name": "الضحى"
    },
    {
        "emotion_id": "comfort",
        "badge": "حين تشعر بأنك وحيد لا نصير لك 🌿",
        "hook": "إن الله معك يسمع خلجات صدرك 🤍",
        "playlist": "معية الله وأمان الروح",
        "surah": 20, "start": 46, "end": 46, "name": "طه"
    },
    {
        "emotion_id": "night_sleep",
        "badge": "أمان لقلبك قبل أن تغمض عينيك 🌙",
        "hook": "تلاوة هادئة لنوم عميق ومطمئن 🕊️",
        "playlist": "سورة الملك قبل النوم",
        "surah": 67, "start": 1, "end": 4, "name": "الملك"
    }
]

RECITERS_POOL = [
    {"id": "Dussary_128kbps", "name": "ياسر الدوسري", "tone": "تلاوة خاشعة"},
    {"id": "Nasser_Alqatami_128kbps", "name": "ناصر القطامي", "tone": "نبرة باكية مؤثرة"},
    {"id": "Fares_Abbad_64kbps", "name": "فارس عباد", "tone": "تلاوة شجية حزينة"},
    {"id": "MaherAlMuaiqly128kbps", "name": "ماهر المعيقلي", "tone": "سكينة الحرم"},
    {"id": "Alafasy_128kbps", "name": "مشاري العفاسي", "tone": "راحة نفسية"},
    {"id": "Abdul_Basit_Murattal_192kbps", "name": "عبد الباسط عبد الصمد", "tone": "تلاوة مهيبة"},
    {"id": "Minshawy_Murattal_128kbps", "name": "محمد صديق المنشاوي", "tone": "خشوع وتدبر"}
]

PINNED_COMMENTS = [
    "اكتب شيئاً تؤجر عليه في ميزان حسناتك 🌿 (سبحان الله، الحمد لله، لا إله إلا الله، الله أكبر) 🤍",
    "شارك الآية لعلها تريح قلباً متعباً الآن وتكون لك صدقة جارية يوم القيامة 🕊️",
    "ما هي أكثر آية تشعرك بالسكينة والطمأنينة عندما تسمعها؟ شاركنا بها في التعليقات 🤍",
    "اللهم اجعل القرآن الكريم ربيع قلوبنا، ونور صدورنا، وجلاء أحزاننا وذهاب همومنا 🤲"
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

def get_chrome_path():
    candidates = ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    os.system("sudo apt-get update && sudo apt-get install -y chromium-browser")
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return "google-chrome"

def clean_arabic_text(text):
    bad_symbols = [
        '۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', 
        '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', 
        '\u06da', '\u06db', '\u06dc', '\u06df', '\u06e0', '\u06e1'
    ]
    for s in bad_symbols:
        text = text.replace(s, '')
    return text.strip()

# ----------------- 2. تقنية الصوت 8D + المطر المحيطي + اللوب الصوتي -----------------
def apply_8d_ambient_sound(raw_audio_path, output_audio_path, duration):
    cmd = [
        "ffmpeg", "-y", "-i", raw_audio_path,
        "-filter_complex",
        (
            f"anoisesrc=d={duration}:c=pink:r=44100:a=0.012,lowpass=f=1100,volume=0.25[ambient];"
            f"[0:a]aecho=0.8:0.88:38|58:0.32|0.22,apulsator=hz=0.09:amount=0.45,volume=1.0[voice];"
            f"[voice][ambient]amix=inputs=2:duration=first:dropout_transition=2,"
            f"afade=t=in:st=0:d=0.4,afade=t=out:st={max(0, duration-0.4)}:d=0.4,"
            f"loudnorm=I=-14:LRA=7:TP=-1.5[out]"
        ),
        "-map", "[out]",
        "-c:a", "aac", "-b:a", "192k",
        output_audio_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_audio_path
    except Exception:
        return raw_audio_path

# ----------------- 3. حركة التقريب السينمائية وتلوين المشاهد -----------------
def apply_ken_burns_and_grade(input_video, output_video, duration):
    print("تطبيق حركة الكاميرا البطيئة وتلوين المشهد...", flush=True)
    vf = (
        f"scale=w='1080*(1+0.05*t/{duration})':h='1920*(1+0.05*t/{duration})':eval=frame,"
        f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,"
        f"eq=contrast=1.12:brightness=-0.04:saturation=1.22,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, duration-0.4)}:d=0.4"
    )
    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        output_video
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_video
    except Exception:
        return input_video

# ----------------- 4. تصميم غلاف متناسق (1:1 Grid Safe) -----------------
def generate_aesthetic_cover(surah_name, reciter_name, emotional_item, font_b64, watermark_handle, output_path="cover.jpg"):
    chrome_bin = get_chrome_path()
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
    <div class="badge">{emotional_item['badge']}</div>
    <div class="surah-title">سُورَةُ {surah_name}</div>
    <div class="reciter">بصوت القارئ {reciter_name}</div>
    <div class="features">🎧 تلاوة 8D بالسماعات • تظليل الكلمات بالذهب 🌿</div>
  </div>
  <div class="watermark">{watermark_handle}</div>
</body></html>"""

    h_file = "temp_cover.html"
    with open(h_file, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(output_path)}", f"file://{os.path.abspath(h_file)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_file):
        os.remove(h_file)
    return output_path

# ----------------- 5. جزيئات الضوء وتظليل الكلمات بالذهب -----------------
def create_atmospheric_particles_overlay(target_width=1080, target_height=1920):
    img = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    random.seed(42)
    for _ in range(45):
        x = random.randint(40, target_width - 40)
        y = random.randint(60, target_height - 60)
        radius = random.randint(3, 14)
        alpha = random.randint(35, 110)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(230, 195, 120, alpha))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=4))
    overlay_path = "particles_layer.png"
    blurred.save(overlay_path, "PNG")
    return overlay_path

def render_word_highlight_html(words, active_idx, emotional_badge, font_b64, watermark_handle):
    chrome_bin = get_chrome_path()
    words_html = []
    for i, w in enumerate(words):
        if i == active_idx:
            words_html.append(f'<span class="word active-gold">{w}</span>')
        else:
            words_html.append(f'<span class="word regular-white">{w}</span>')

    full_verse_html = " ".join(words_html)
    font_size = 70 if len(words) <= 6 else (58 if len(words) <= 13 else 46)

    html_code = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'AmiriQuran'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }}
  .emotional-badge {{ position: absolute; top: 190px; background: rgba(10, 14, 20, 0.55); border: 1px solid rgba(212, 175, 55, 0.45); color: #F9FAFB; font-family: 'AmiriQuran'; font-size: 26px; padding: 10px 28px; border-radius: 30px; direction: rtl; }}
  .ayah-container {{ direction: rtl; text-align: center; font-family: 'AmiriQuran'; font-size: {font_size}px; font-weight: bold; line-height: 1.95; max-width: 930px; margin: auto 0; }}
  .word {{ display: inline-block; margin: 0 4px; }}
  .regular-white {{ color: #FFFFFF; text-shadow: 0 0 10px rgba(0, 0, 0, 0.95), 0 4px 18px rgba(0, 0, 0, 0.9); }}
  .active-gold {{ color: #D4AF37 !important; text-shadow: 0 0 15px rgba(212, 175, 55, 0.9), 0 0 35px rgba(212, 175, 55, 0.6); }}
  .watermark {{ position: absolute; bottom: 110px; left: 50%; transform: translateX(-50%); font-family: 'AmiriQuran'; font-size: 24px; color: rgba(255, 255, 255, 0.45); direction: ltr; }}
</style></head>
<body>
  <div class="emotional-badge">🎧 ضع السماعات • {emotional_badge}</div>
  <div class="ayah-container">{full_verse_html}</div>
  <div class="watermark">{watermark_handle}</div>
</body></html>"""

    html_file = f"temp_frame_{active_idx}.html"
    png_file = f"frame_highlight_{active_idx}.png"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_code)

    cmd = [chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(png_file)}", f"file://{os.path.abspath(html_file)}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(html_file):
        os.remove(html_file)
    return png_file

# ----------------- 6. جلب الآيات والخلفيات -----------------
def fetch_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id, reciter_name):
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    surah_name = requests.get(meta_url, timeout=15).json().get("data", {}).get("name", f"سورة {surah_num}")

    ayahs_list = []
    for a_num in range(start_ayah, end_ayah + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/quran-simple", timeout=15).json()
        cleaned_text = clean_arabic_text(t_res.get("data", {}).get("text", ""))

        if a_num == 1 and surah_num != 1:
            cleaned_text = cleaned_text.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        surah_str = f"{surah_num:03d}"
        ayah_str = f"{a_num:03d}"
        aud_url = f"https://everyayah.com/data/{reciter_id}/{surah_str}{ayah_str}.mp3"
        fallback_aud = f"https://everyayah.com/data/Alafasy_128kbps/{surah_str}{ayah_str}.mp3"

        aud_file = f"audio_{a_num}.mp3"
        try:
            r = requests.get(aud_url, timeout=25)
            if r.status_code == 200 and len(r.content) > 3000:
                with open(aud_file, "wb") as f:
                    f.write(r.content)
            else:
                with open(aud_file, "wb") as f:
                    f.write(requests.get(fallback_aud, timeout=25).content)
        except Exception:
            with open(aud_file, "wb") as f:
                f.write(requests.get(fallback_aud, timeout=25).content)

        ayahs_list.append({
            "number": a_num,
            "text": cleaned_text,
            "audio_path": aud_file
        })

    ayah_range = f"{start_ayah}-{end_ayah}" if start_ayah != end_ayah else f"{start_ayah}"
    return ayahs_list, surah_name, ayah_range, reciter_name

def download_scenic_nature_video():
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}

    queries = [
        "switzerland mountains drone vertical",
        "scenic mountains clouds aerial vertical",
        "norway green mountains drone vertical",
        "foggy mountain valley cinematic vertical"
    ]
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=12"
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        videos = res.get("videos", [])
        if videos:
            chosen = random.choice(videos)
            video_files = sorted(chosen["video_files"], key=lambda x: x.get("width", 0))
            best_link = video_files[-1]["link"]
            with open("bg_raw.mp4", "wb") as f:
                f.write(requests.get(best_link, timeout=35).content)
            return "bg_raw.mp4"
    except Exception:
        pass
    return "bg_raw.mp4"

# ----------------- 7. المونتاج المتكامل -----------------
def build_advanced_quran_video(ayahs_list, emotional_item, watermark_handle):
    font_b64 = get_font_base64()
    audio_clips, text_overlay_clips = [], []
    current_time = 0.0

    for ayah in ayahs_list:
        a_clip = AudioFileClip(ayah["audio_path"])
        ayah_duration = a_clip.duration
        audio_clips.append(a_clip)

        words = ayah["text"].split()
        if not words:
            continue

        total_chars = sum(len(w) for w in words)
        word_start_time = current_time

        for w_idx, w in enumerate(words):
            w_duration = (len(w) / total_chars) * ayah_duration
            frame_img = render_word_highlight_html(words, w_idx, emotional_item["badge"], font_b64, watermark_handle)
            t_clip = ImageClip(frame_img).set_start(word_start_time).set_duration(w_duration).set_position(("center", "center"))
            text_overlay_clips.append(t_clip)
            word_start_time += w_duration

        current_time += ayah_duration

    merged_raw_audio = concatenate_audioclips(audio_clips)
    merged_raw_audio.write_audiofile("temp_raw_audio.mp3", fps=44100, logger=None)

    total_duration = current_time + 1.0

    final_8d_audio_path = apply_8d_ambient_sound("temp_raw_audio.mp3", "final_8d_audio.mp3", total_duration)
    final_audio = AudioFileClip(final_8d_audio_path)

    graded_video_path = apply_ken_burns_and_grade("bg_raw.mp4", "bg_cinematic.mp4", total_duration)
    bg_clip = VideoFileClip(graded_video_path).resize((1080, 1920))

    dim_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.20).set_duration(total_duration)
    particles_file = create_atmospheric_particles_overlay()
    particles_clip = ImageClip(particles_file).set_duration(total_duration).set_opacity(0.65)

    active_layers = [bg_clip, dim_overlay, particles_clip] + text_overlay_clips

    final = CompositeVideoClip(active_layers).set_audio(final_audio)
    final.write_videofile("final_reel.mp4", fps=24, codec="libx264", audio_codec="aac", bitrate="2800k", threads=4, preset="ultrafast")
    return "final_reel.mp4"

# ----------------- 8. نظام الرفع المحمي ضد الأخطاء (مع خوادم CDN بديلة) -----------------
def upload_to_catbox(file_path):
    """خادم احتياطي مجاني فائق السرعة يعطي رابط مباشر دائم للملف"""
    try:
        print("الرفع الاحتياطي عبر خادم Catbox المباشر...", flush=True)
        with open(file_path, "rb") as f:
            res = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=60
            )
        if res.status_code == 200 and res.text.startswith("http"):
            return res.text.strip()
    except Exception as e:
        print(f"Catbox upload error: {e}", flush=True)
    return None

def upload_files_to_github_release(video_file="final_reel.mp4", cover_file="cover.jpg"):
    print("محاولة الرفع إلى GitHub Releases...", flush=True)
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    tag_name = f"reel-{int(random.random()*1000000000)}"

    if repo and gh_token:
        create_url = f"https://api.github.com/repos/{repo}/releases"
        headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
        rel_data = {"tag_name": tag_name, "name": f"Reel Release {tag_name}", "draft": False, "prerelease": False}
        try:
            res = requests.post(create_url, headers=headers, json=rel_data, timeout=20).json()
            if "upload_url" in res:
                upload_url = res["upload_url"].split("{")[0]
                with open(video_file, "rb") as f:
                    up_res = requests.post(
                        f"{upload_url}?name=final_reel.mp4",
                        headers={"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"},
                        data=f, timeout=60
                    ).json()
                pub_url = up_res.get("browser_download_url")

                if os.path.exists(cover_file):
                    with open(cover_file, "rb") as f_cov:
                        requests.post(
                            f"{upload_url}?name=cover.jpg",
                            headers={"Authorization": f"token {gh_token}", "Content-Type": "image/jpeg"},
                            data=f_cov, timeout=30
                        )
                if pub_url:
                    print(f"✅ تم الرفع بنجاح عبر GitHub Release: {pub_url}", flush=True)
                    return pub_url
            else:
                print(f"⚠️ تنبيه من GitHub API (صلاحيات القراءة فقط): {res}", flush=True)
        except Exception as e:
            print(f"⚠️ خطأ أثناء محاولة الرفع لـ GitHub: {e}", flush=True)

    # إذا فشل GitHub Release لأي سبب، يتم الرفع فوراً عبر Catbox البديل
    fallback_url = upload_to_catbox(video_file)
    if fallback_url:
        print(f"✅ تم رفع الفيديو بنجاح عبر السيرفر البديل: {fallback_url}", flush=True)
        return fallback_url

    raise RuntimeError("تعذر رفع الفيديو عبر GitHub Release أو السيرفر البديل.")

def get_channel_service(ch_id, headers, graphql_url):
    query = """query GetChannel($input: ChannelInput!) { channel(input: $input) { service } }"""
    try:
        r = requests.post(graphql_url, headers=headers, json={"query": query, "variables": {"input": {"id": ch_id}}}, timeout=10)
        return r.json().get("data", {}).get("channel", {}).get("service", "").lower()
    except Exception:
        return ""

def post_to_buffer(video_url, s_name, emotional_badge, caption):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        return

    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
    graphql_url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {buffer_token}", "Content-Type": "application/json"}

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id status } }
        ... on MutationError { message }
      }
    }
    """

    for ch_id in channel_ids:
        service = get_channel_service(ch_id, headers, graphql_url)
        post_input = {
            "channelId": ch_id,
            "text": caption,
            "mode": "shareNow",
            "schedulingType": "automatic",
            "assets": [{"video": {"url": video_url}}]
        }

        # عنوان يوتيوب القصير الآمن تماماً
        if service == "youtube" or ch_id == "6aa72b30ea19ca0bde39598b":
            yt_clean_title = f"{emotional_badge[:28]} | سورة {s_name} 🤍 #shorts"[:60]
            post_input["metadata"] = {
                "youtube": {
                    "title": yt_clean_title,
                    "categoryId": "27"
                }
            }
        elif service == "instagram" or ch_id == "6aa6d1fbea19ca0bde35e91c":
            post_input["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}

        try:
            res = requests.post(graphql_url, headers=headers, json={"query": mutation, "variables": {"input": post_input}}, timeout=30)
            data = res.json()
            err_msg = ""
            if "errors" in data and data["errors"]:
                err_msg = data['errors'][0].get('message', str(data['errors']))
            elif "data" in data and data.get("data", {}).get("createPost", {}).get("message"):
                err_msg = data['data']['createPost']['message']

            if err_msg:
                print(f"⚠️ رد القناة {ch_id}: {err_msg}", flush=True)
            else:
                print(f"✅ تم النشر بنجاح على القناة: {ch_id}", flush=True)
        except Exception as e:
            print(f"❌ خطأ أثناء النشر للقناة {ch_id}: {e}", flush=True)

def notify_telegram(message, cover_path=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)

        if cover_path and os.path.exists(cover_path):
            photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            with open(cover_path, "rb") as pf:
                requests.post(
                    photo_url,
                    data={"chat_id": chat_id, "caption": "📸 <b>غلاف المقطع المخصص (1:1 Grid Safe)</b> جاهز للإنستغرام ويوتيوب 🌿", "parse_mode": "HTML"},
                    files={"photo": pf},
                    timeout=20
                )
    except Exception as e:
        print(f"Telegram error: {e}", flush=True)

if __name__ == "__main__":
    print("=== بدء إنتاج فيديو القرآن الفيروسي ===", flush=True)
    emotion_item = random.choice(EMOTIONAL_PHARMACY)
    reciter_info = random.choice(RECITERS_POOL)
    watermark_handle = os.getenv("WATERMARK_HANDLE", "@quran_reels").strip()
    selected_pinned_comment = random.choice(PINNED_COMMENTS)

    font_b64 = get_font_base64()

    ayahs, s_name, a_range, r_name = fetch_ayahs_data(
        emotion_item["surah"], emotion_item["start"], emotion_item["end"],
        reciter_info["id"], reciter_info["name"]
    )

    download_scenic_nature_video()
    build_advanced_quran_video(ayahs, emotion_item, watermark_handle)

    cover_path = generate_aesthetic_cover(s_name, r_name, emotion_item, font_b64, watermark_handle, "cover.jpg")
    pub_url = upload_files_to_github_release("final_reel.mp4", cover_path)

    full_caption = (
        f"{emotion_item['hook']}\n\n"
        f"📖 سورة {s_name} ({a_range})\n"
        f"🎙️ القارئ: {r_name} (تلاوة 8D بالسماعات 🎧)\n"
        f"📁 {emotion_item['playlist']}\n\n"
        f"ضع إعجاباً وشاركها لعلها تريح قلباً متعباً الآن 🤍\n\n"
        f"#تلاوة_8d #راحة_نفسية #صيدلية_المشاعر #سورة_{s_name.replace(' ', '_')} "
        f"#{r_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )

    post_to_buffer(pub_url, s_name, emotion_item["badge"], full_caption)

    tg_report = (
        f"✨ <b>تم إنتاج ونشر المقطع بنجاح!</b>\n\n"
        f"📖 <b>السورة:</b> {s_name} ({a_range})\n"
        f"🎙️ <b>القارئ:</b> {r_name}\n"
        f"🔗 <b>رابط المقطع:</b> <a href='{pub_url}'>اضغط هنا للمشاهدة</a>\n\n"
        f"📌 <b>التعليق المقترح للتثبيت:</b>\n"
        f"<code>{selected_pinned_comment}</code>"
    )
    notify_telegram(tg_report, cover_path)
    print("=== اكتمل خط الإنتاج بنجاح ===", flush=True)

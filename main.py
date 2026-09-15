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
        "badge": "رسالة لقلبك إذا كنت حزيناً أو متعباً 🌿",
        "hook": "إذا ضاقت بك الدنيا وتعب قلبك.. استمع لرسالة الله إليك 🤍",
        "playlist": "سكينة القلوب وتفريج الهموم",
        "surah": 94, "start": 1, "end": 8, "name": "الشرح"
    },
    {
        "emotion_id": "anxiety",
        "badge": "إذا كنت قلقاً من المستقبل أو الرزق 🕊️",
        "hook": "اطمئن على رزقك ومستقبلك.. الأمر كله بيد الله 🌿",
        "playlist": "آيات الرزق والفرج العاجل",
        "surah": 65, "start": 2, "end": 3, "name": "الطلاق"
    },
    {
        "emotion_id": "peace",
        "badge": "تلاوة تنزل السكينة والأمان على روحك 🤍",
        "hook": "أرح سمعك وفؤادك من صخب الدنيا وضغوطها 🕊️",
        "playlist": "رفيق النوم والسكينة",
        "surah": 13, "start": 28, "end": 28, "name": "الرعد"
    },
    {
        "emotion_id": "hope",
        "badge": "مهما بلغت ذنوبك وتثاقلت خطاك.. ربك غفور 🌧️",
        "hook": "بداية جديدة وأمل يتجدد مع آيات المغفرة والرحمة 🤍",
        "playlist": "أبواب التوبة والرجاء",
        "surah": 93, "start": 1, "end": 5, "name": "الضحى"
    },
    {
        "emotion_id": "comfort",
        "badge": "حين تشعر بأنك وحيد لا نصير لك 🌿",
        "hook": "إن الله معك يسمع دبيب نملتك وخلجات صدرك 🤍",
        "playlist": "معية الله وأمان الروح",
        "surah": 20, "start": 46, "end": 46, "name": "طه"
    },
    {
        "emotion_id": "night_sleep",
        "badge": "أمان وحصن لقلبك قبل أن تغمض عينيك 🌙",
        "hook": "تلاوة هادئة تعينك على نوم مطمئن وسكينة تامة 🕊️",
        "playlist": "سورة الملك قبل النوم",
        "surah": 67, "start": 1, "end": 4, "name": "الملك"
    }
]

# باقة القراء الأكثر انتشاراً وتأثيراً
RECITERS_POOL = [
    {"id": "Dussary_128kbps", "name": "ياسر الدوسري", "tone": "تلاوة خاشعة تهز القلوب"},
    {"id": "Nasser_Alqatami_128kbps", "name": "ناصر القطامي", "tone": "نبرة باكية مؤثرة"},
    {"id": "Fares_Abbad_64kbps", "name": "فارس عباد", "tone": "تلاوة شجية حزينة"},
    {"id": "MaherAlMuaiqly128kbps", "name": "ماهر المعيقلي", "tone": "سكينة وطمأنينة الحرم"},
    {"id": "Alafasy_128kbps", "name": "مشاري العفاسي", "tone": "راحة نفسية وهدوء للبال"},
    {"id": "Abdul_Basit_Murattal_192kbps", "name": "عبد الباسط عبد الصمد", "tone": "تلاوة مهيبة تأسر الروح"},
    {"id": "Minshawy_Murattal_128kbps", "name": "محمد صديق المنشاوي", "tone": "خشوع وتدبر عميق"}
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

# ----------------- 2. معالجة الصوت 8D + المطر المحيطي الخافت -----------------
def apply_8d_ambient_sound(raw_audio_path, output_audio_path, duration):
    """
    تطبيق فلتر 8D Reverb + توليد صوت مطر خافت طبيعي (-22dB) ومعايرة الصوت بمواصفات البث
    """
    print("تطبيق هندسة الصوت 8D ومزج المطر المحيطي عبر FFmpeg...", flush=True)
    cmd = [
        "ffmpeg", "-y", "-i", raw_audio_path,
        "-filter_complex",
        (
            f"anoisesrc=d={duration}:c=pink:r=44100:a=0.012,lowpass=f=1100,volume=0.25[ambient];"
            f"[0:a]aecho=0.8:0.88:38|58:0.32|0.22,apulsator=hz=0.09:amount=0.45,volume=1.0[voice];"
            f"[voice][ambient]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=7:TP=-1.5[out]"
        ),
        "-map", "[out]",
        "-c:a", "aac", "-b:a", "192k",
        output_audio_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_audio_path
    except Exception as e:
        print(f"8D DSP warning: {e}, fallback to raw audio", flush=True)
        return raw_audio_path

# ----------------- 3. توليد طبقة ذرات الغبار المضيئة (Particles) -----------------
def create_atmospheric_particles_overlay(target_width=1080, target_height=1920):
    """رسم طبقة ذرات ضوء ذهبية مضيئة سينمائية تطفو فوق المشهد"""
    img = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # توليد 45 ذرة غبار عشوائية ناعمة
    random.seed(42)
    for _ in range(45):
        x = random.randint(40, target_width - 40)
        y = random.randint(60, target_height - 60)
        radius = random.randint(3, 14)
        alpha = random.randint(35, 110)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(230, 195, 120, alpha)
        )

    blurred = img.filter(ImageFilter.GaussianBlur(radius=4))
    overlay_path = "particles_layer.png"
    blurred.save(overlay_path, "PNG")
    return overlay_path

# ----------------- 4. تظليل الكلمات كلمة بكلمة بالذهب (Karaoke Highlight) -----------------
def render_word_highlight_html(words, active_idx, emotional_badge, font_b64, watermark_handle):
    chrome_bin = get_chrome_path()

    words_html = []
    for i, w in enumerate(words):
        if i == active_idx:
            # الكلمة المقروءة حالياً تضيء باللون الذهبي الخالص
            words_html.append(f'<span class="word active-gold">{w}</span>')
        else:
            words_html.append(f'<span class="word regular-white">{w}</span>')

    full_verse_html = " ".join(words_html)
    font_size = 70 if len(words) <= 6 else (58 if len(words) <= 13 else 46)

    html_code = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
  @font-face {{
    font-family: 'AmiriQuran';
    src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype');
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px;
    height: 1920px;
    background: transparent;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    position: relative;
  }}
  .emotional-badge {{
    position: absolute;
    top: 190px;
    background: rgba(10, 14, 20, 0.55);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(212, 175, 55, 0.45);
    color: #F9FAFB;
    font-family: 'AmiriQuran', sans-serif;
    font-size: 26px;
    padding: 10px 28px;
    border-radius: 30px;
    letter-spacing: 1px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.6);
    direction: rtl;
  }}
  .ayah-container {{
    direction: rtl;
    text-align: center;
    font-family: 'AmiriQuran', serif;
    font-size: {font_size}px;
    font-weight: bold;
    line-height: 1.95;
    max-width: 930px;
    margin: auto 0;
  }}
  .word {{
    display: inline-block;
    margin: 0 4px;
    transition: all 0.2s ease;
  }}
  .regular-white {{
    color: #FFFFFF;
    text-shadow: 
      0 0 10px rgba(0, 0, 0, 0.95),
      0 4px 18px rgba(0, 0, 0, 0.9);
  }}
  .active-gold {{
    color: #D4AF37 !important;
    transform: scale(1.08);
    text-shadow: 
      0 0 15px rgba(212, 175, 55, 0.9),
      0 0 35px rgba(212, 175, 55, 0.6),
      0 4px 18px rgba(0, 0, 0, 0.95);
  }}
  .watermark {{
    position: absolute;
    bottom: 110px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'AmiriQuran', sans-serif;
    font-size: 24px;
    color: rgba(255, 255, 255, 0.45);
    letter-spacing: 2px;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85);
    direction: ltr;
  }}
</style>
</head>
<body>
  <div class="emotional-badge">🎧 ضع السماعات • {emotional_badge}</div>
  <div class="ayah-container">{full_verse_html}</div>
  <div class="watermark">{watermark_handle}</div>
</body>
</html>"""

    html_file = f"temp_frame_{active_idx}.html"
    png_file = f"frame_highlight_{active_idx}.png"

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_code)

    cmd = [
        chrome_bin, "--headless", "--no-sandbox", "--disable-gpu",
        "--window-size=1080,1920", "--default-background-color=00000000",
        f"--screenshot={os.path.abspath(png_file)}",
        f"file://{os.path.abspath(html_file)}"
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(html_file):
        os.remove(html_file)
    return png_file

# ----------------- 5. بناء الفيديو السينمائي الكامل -----------------
def fetch_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id, reciter_name):
    print(f"جلب آيات سورة {surah_num} بصوت {reciter_name}...", flush=True)
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
    print("تنزيل خلفية طبيعية فائقة الجودة من Pexels...", flush=True)
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
            with open("bg_video.mp4", "wb") as f:
                f.write(requests.get(best_link, timeout=35).content)
            return "bg_video.mp4"
    except Exception as e:
        print(f"Pexels warning: {e}", flush=True)
    return "bg_video.mp4"

def build_advanced_quran_video(ayahs_list, emotional_item, watermark_handle):
    print("مونتاج الفيديو بنظام تظليل الكلمات بالذهب والذرات السينمائية...", flush=True)
    font_b64 = get_font_base64()

    audio_clips = []
    text_overlay_clips = []
    current_time = 0.0

    # بناء طبقات الكلمات المتزامنة كلمة بكلمة
    for ayah in ayahs_list:
        a_clip = AudioFileClip(ayah["audio_path"])
        ayah_duration = a_clip.duration
        audio_clips.append(a_clip)

        words = ayah["text"].split()
        if not words:
            continue

        # حساب التوقيت النسبي لكل كلمة بناءً على عدد الحروف
        total_chars = sum(len(w) for w in words)
        word_start_time = current_time

        for w_idx, w in enumerate(words):
            w_duration = (len(w) / total_chars) * ayah_duration
            frame_img = render_word_highlight_html(
                words, w_idx, emotional_item["badge"], font_b64, watermark_handle
            )
            t_clip = (
                ImageClip(frame_img)
                .set_start(word_start_time)
                .set_duration(w_duration)
                .set_position(("center", "center"))
            )
            text_overlay_clips.append(t_clip)
            word_start_time += w_duration

        current_time += ayah_duration

    # دمج الصوت ومعالجة الـ 8D + المطر المحيطي
    merged_raw_audio = concatenate_audioclips(audio_clips)
    merged_raw_audio.write_audiofile("temp_raw_audio.mp3", fps=44100, logger=None)

    total_duration = current_time + 1.0
    final_8d_audio_path = apply_8d_ambient_sound("temp_raw_audio.mp3", "final_8d_audio.mp3", total_duration)
    final_audio = AudioFileClip(final_8d_audio_path)

    # ضبط فيديو الخلفية
    bg_clip = VideoFileClip("bg_video.mp4")
    if bg_clip.duration < total_duration:
        bg_clip = bg_clip.loop(duration=total_duration)
    else:
        bg_clip = bg_clip.subclip(0, total_duration)
    bg_clip = bg_clip.resize((1080, 1920))

    # طبقة تباين وتعتيم هادئة
    dim_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.22).set_duration(total_duration)

    # طبقة جزيئات الضوء الذهبية (Particles)
    particles_file = create_atmospheric_particles_overlay()
    particles_clip = ImageClip(particles_file).set_duration(total_duration).set_opacity(0.65)

    final = CompositeVideoClip([bg_clip, dim_overlay, particles_clip] + text_overlay_clips).set_audio(final_audio)

    final.write_videofile(
        "final_reel.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="2800k",
        threads=4,
        preset="ultrafast"
    )
    return "final_reel.mp4"

def upload_video_to_github_release():
    print("رفع الفيديو إلى GitHub Releases...", flush=True)
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    tag_name = f"reel-{int(random.random()*1000000000)}"

    create_url = f"https://api.github.com/repos/{repo}/releases"
    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    rel_data = {"tag_name": tag_name, "name": f"Reel Release {tag_name}", "draft": False, "prerelease": False}
    res = requests.post(create_url, headers=headers, json=rel_data, timeout=20).json()
    upload_url = res["upload_url"].split("{")[0]

    with open("final_reel.mp4", "rb") as f:
        up_headers = {"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}
        up_res = requests.post(f"{upload_url}?name=final_reel.mp4", headers=up_headers, data=f, timeout=60).json()

    return up_res.get("browser_download_url")

def get_channel_service(ch_id, headers, graphql_url):
    query = """query GetChannel($input: ChannelInput!) { channel(input: $input) { service } }"""
    try:
        r = requests.post(graphql_url, headers=headers, json={"query": query, "variables": {"input": {"id": ch_id}}}, timeout=10)
        return r.json().get("data", {}).get("channel", {}).get("service", "").lower()
    except Exception:
        return ""

def post_to_buffer(video_url, video_title, caption):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        print("بيانات Buffer غير مكتملة، تم تخطي النشر.", flush=True)
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

        if service == "youtube" or ch_id == "6aa72b30ea19ca0bde39598b":
            post_input["metadata"] = {"youtube": {"title": video_title[:100], "categoryId": "27"}}
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

def notify_telegram(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception as e:
        print(f"Telegram notify error: {e}", flush=True)

if __name__ == "__main__":
    print("=== بدء إنتاج فيديو القرآن الفيروسي (الجيل الجديد 8D + صيدلية المشاعر) ===", flush=True)
    emotion_item = random.choice(EMOTIONAL_PHARMACY)
    reciter_info = random.choice(RECITERS_POOL)
    watermark_handle = os.getenv("WATERMARK_HANDLE", "@quran_reels").strip()
    selected_pinned_comment = random.choice(PINNED_COMMENTS)

    notify_telegram(
        f"🎬 جاري إنتاج ريلز استثنائي:\n"
        f"• {emotion_item['badge']}\n"
        f"• سورة {emotion_item['name']} بصوت {reciter_info['name']} (8D Audio + المطر والذهب)..."
    )

    ayahs, s_name, a_range, r_name = fetch_ayahs_data(
        emotion_item["surah"], emotion_item["start"], emotion_item["end"],
        reciter_info["id"], reciter_info["name"]
    )

    download_scenic_nature_video()
    build_advanced_quran_video(ayahs, emotion_item, watermark_handle)
    pub_url = upload_video_to_github_release()

    video_title = f"{emotion_item['hook']} | سورة {s_name} بصوت {r_name} (8D)"[:100]
    full_caption = (
        f"{emotion_item['hook']}\n\n"
        f"📖 سورة {s_name} ({a_range})\n"
        f"🎙️ القارئ: {r_name} (تلاوة 8D بالسماعات 🎧)\n"
        f"📁 {emotion_item['playlist']}\n\n"
        f"ضع إعجاباً وشاركها لعلها تريح قلباً متعباً الآن 🤍\n\n"
        f"#تلاوة_8d #راحة_نفسية #صيدلية_المشاعر #سورة_{s_name.replace(' ', '_')} "
        f"#{r_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )

    post_to_buffer(pub_url, video_title, full_caption)

    tg_report = (
        f"✨ تم النشر بنجاح على جميع المنصات بنظام الـ 8D والذهب!\n"
        f"العنوان: {video_title}\n"
        f"الرابط: {pub_url}\n\n"
        f"📌 التعليق التفاعلي للتثبيت:\n"
        f"<code>{selected_pinned_comment}</code>"
    )
    notify_telegram(tg_report)
    print("=== اكتمل خط الإنتاج الفيروسي بنجاح ===", flush=True)

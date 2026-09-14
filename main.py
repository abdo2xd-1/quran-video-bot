import os
import sys
import json
import random
import re
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips
)

# باقة مختارة: سور كاملة ومقاطع لا تقل عن 3 آيات متناسقة للمنصات
QURAN_PLAYLIST = [
    {"surah": 108, "start": 1, "end": 3, "name": "الكوثر"},  # سورة كاملة (3 آيات)
    {"surah": 103, "start": 1, "end": 3, "name": "العصر"},   # سورة كاملة (3 آيات)
    {"surah": 112, "start": 1, "end": 4, "name": "الإخلاص"}, # سورة كاملة (4 آيات)
    {"surah": 113, "start": 1, "end": 5, "name": "الفلق"},   # سورة كاملة (5 آيات)
    {"surah": 114, "start": 1, "end": 6, "name": "الناس"},   # سورة كاملة (6 آيات)
    {"surah": 97,  "start": 1, "end": 5, "name": "القدر"},   # سورة كاملة (5 آيات)
    {"surah": 94,  "start": 1, "end": 8, "name": "الشرح"},   # سورة كاملة (8 آيات)
    {"surah": 95,  "start": 1, "end": 8, "name": "التين"},   # سورة كاملة (8 آيات)
    {"surah": 1,   "start": 1, "end": 7, "name": "الفاتحة"}, # سورة كاملة (7 آيات)
    {"surah": 67,  "start": 1, "end": 4, "name": "الملك"},   # 4 آيات
    {"surah": 55,  "start": 1, "end": 5, "name": "الرحمن"},  # 5 آيات
    {"surah": 93,  "start": 1, "end": 5, "name": "الضحى"}    # 5 آيات
]

RECITERS_POOL = [
    ("ar.alafasy", "مشاري العفاسي"),
    ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد"),
    ("ar.husary", "محمود خليل الحصري"),
    ("ar.minshawi", "محمد صديق المنشاوي")
]

FONT_CDN_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

def ensure_font():
    """تحميل خط المصحف الشريف Amiri Bold"""
    font_path = "Amiri-Bold.ttf"
    if not os.path.exists(font_path) or os.path.getsize(font_path) < 40000:
        try:
            r = requests.get(FONT_CDN_URL, timeout=20)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Font download fallback: {e}", flush=True)

    if os.path.exists(font_path) and os.path.getsize(font_path) > 40000:
        return font_path

    for sys_font in [
        "/usr/share/fonts/truetype/amiri/Amiri-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"
    ]:
        if os.path.exists(sys_font):
            return sys_font
    return None

def clean_arabic_text(text):
    """إزالة علامات الوقف العثمانية التي تفسد اتصال الحروف"""
    bad_symbols = ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']
    for sym in bad_symbols:
        text = text.replace(sym, '')
    return text.strip()

def shape_text(text):
    """تشبيك الحروف وضبط اتجاه القراءة مع المحافظة التامة على التشكيل"""
    reshaper = arabic_reshaper.ArabicReshaper({
        'delete_harakat': False,
        'support_ligatures': True
    })
    return get_display(reshaper.reshape(text))

def fetch_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id, reciter_name):
    print(f"جلب آيات سورة {surah_num} من {start_ayah} إلى {end_ayah}...", flush=True)
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    surah_name = requests.get(meta_url, timeout=15).json().get("data", {}).get("name", f"سورة {surah_num}")

    ayahs_list = []

    for a_num in range(start_ayah, end_ayah + 1):
        url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/{reciter_id}"
        res = requests.get(url, timeout=15).json()
        
        if res.get("status") == "OK" and "data" in res:
            raw_text = res["data"].get("text", "")
            cleaned_text = clean_arabic_text(raw_text)

            # إزالة البسملة إذا كانت مدمجة في أول آية لغير الفاتحة
            if a_num == 1 and surah_num != 1:
                cleaned_text = cleaned_text.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

            audio_url = res["data"].get("audio")
            if not audio_url:
                fb = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/ar.alafasy", timeout=15).json()
                audio_url = fb.get("data", {}).get("audio")

            audio_filename = f"audio_{a_num}.mp3"
            with open(audio_filename, "wb") as f:
                f.write(requests.get(audio_url, timeout=25).content)

            ayahs_list.append({
                "number": a_num,
                "text": cleaned_text,
                "audio_path": audio_filename
            })

    if not ayahs_list:
        raise ValueError("فشل في تحميل آيات السورة.")

    ayah_range = f"{start_ayah}-{end_ayah}" if start_ayah != end_ayah else f"{start_ayah}"
    return ayahs_list, surah_name, ayah_range, reciter_name

def download_scenic_nature_video():
    """جلب لقطة درون هادئة لجبال وبحيرات خضراء من Pexels"""
    print("تنزيل خلفية جبال طبيعية هادئة...", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}

    queries = [
        "switzerland mountains drone vertical",
        "alps landscape sunny green valley",
        "scenic mountains clouds aerial vertical",
        "norway green mountains drone vertical",
        "nature green valley aerial 4k vertical"
    ]
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"

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

def create_single_ayah_image(text, index, target_width=1080, target_height=1920):
    """توليد صورة مخصصة لكل آية لتظهر في منتصف الشاشة مع الظل الأسود"""
    font_file = ensure_font()

    img = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    words = text.split()
    # توزيع الكلمات لأسطر مريحة (بحد أقصى 4 كلمات في السطر)
    lines = []
    w_per_line = 3 if len(words) <= 6 else 4
    for i in range(0, len(words), w_per_line):
        chunk = " ".join(words[i:i + w_per_line])
        lines.append(shape_text(chunk))

    multiline_text = "\n".join(lines)

    # ضبط حجم الخط حسب طول الآية
    if len(words) <= 5:
        font_size = 72
    elif len(words) <= 12:
        font_size = 60
    else:
        font_size = 48

    font = ImageFont.truetype(font_file, font_size) if font_file else ImageFont.load_default()

    center_x = target_width // 2
    center_y = target_height // 2

    # رسم الظل المحيط لبروز النص الأبيض
    for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (0, -4), (4, 0), (-4, 0)]:
        draw.multiline_text(
            (center_x + ox, center_y + oy),
            multiline_text,
            font=font,
            fill=(0, 0, 0, 240),
            align="center",
            anchor="mm",
            spacing=32
        )

    # رسم الآية باللون الأبيض
    draw.multiline_text(
        (center_x, center_y),
        multiline_text,
        font=font,
        fill=(255, 255, 255, 255),
        align="center",
        anchor="mm",
        spacing=32
    )

    out_name = f"ayah_overlay_{index}.png"
    img.save(out_name, "PNG")
    return out_name

def build_synchronized_video(ayahs_list):
    print("مونتاج الفيديو وتزامن كل آية بدقة مع صوتها...", flush=True)

    audio_clips = []
    text_overlay_clips = []
    current_time = 0.0

    for idx, ayah in enumerate(ayahs_list):
        a_clip = AudioFileClip(ayah["audio_path"])
        duration = a_clip.duration
        audio_clips.append(a_clip)

        # إنشاء صورة الآية وضبط ظهورها واختفائها مع التوقيت الصوتي
        img_path = create_single_ayah_image(ayah["text"], idx)
        t_clip = (
            ImageClip(img_path)
            .set_start(current_time)
            .set_duration(duration)
            .set_position(("center", "center"))
        )
        text_overlay_clips.append(t_clip)
        current_time += duration

    # دمج الأصوات بالتسلسل التام
    final_audio = concatenate_audioclips(audio_clips)
    total_duration = current_time + 0.8

    # ضبط وتكرار فيديو الخلفية
    bg_clip = VideoFileClip("bg_video.mp4")
    if bg_clip.duration < total_duration:
        bg_clip = bg_clip.loop(duration=total_duration)
    else:
        bg_clip = bg_clip.subclip(0, total_duration)

    bg_clip = bg_clip.resize((1080, 1920))

    # طبقة تباين سينمائية ناعمة
    dim_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.25).set_duration(total_duration)

    final = CompositeVideoClip([bg_clip, dim_overlay] + text_overlay_clips).set_audio(final_audio)

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
    query = """
    query GetChannel($input: ChannelInput!) {
      channel(input: $input) {
        service
      }
    }
    """
    try:
        r = requests.post(graphql_url, headers=headers, json={"query": query, "variables": {"input": {"id": ch_id}}}, timeout=10)
        return r.json().get("data", {}).get("channel", {}).get("service", "").lower()
    except Exception:
        return ""

def post_to_buffer(video_url, surah_name, ayah_range, reciter_name):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        print("بيانات Buffer غير مكتملة، تم تخطي النشر.", flush=True)
        return

    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
    caption = (
        f"سورة {surah_name} 🤍 (الآيات {ayah_range})\n"
        f"القارئ: {reciter_name}\n\n"
        f"أرح قلبك ومسمعك بآيات الله 🌿\n\n"
        f"#قرآن #تلاوة_خاشعة #راحة_نفسية #سورة_{surah_name.replace(' ', '_')} "
        f"#{reciter_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )
    video_title = f"سورة {surah_name} ({ayah_range}) | تلاوة خاشعة بصوت {reciter_name}"

    graphql_url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {buffer_token}", "Content-Type": "application/json"}

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            status
          }
        }
        ... on MutationError {
          message
        }
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
    print("=== بدء إنتاج فيديو متزامن آية بآية ===", flush=True)
    item = random.choice(QURAN_PLAYLIST)
    rec = random.choice(RECITERS_POOL)

    notify_telegram(f"🎬 جاري إنتاج فيديو متزامن:\nسورة {item['name']} ({item['start']}-{item['end']}) بصوت {rec[1]}...")

    ayahs, s_name, a_range, r_name = fetch_ayahs_data(
        item["surah"], item["start"], item["end"], rec[0], rec[1]
    )

    download_scenic_nature_video()
    build_synchronized_video(ayahs)
    pub_url = upload_video_to_github_release()

    post_to_buffer(pub_url, s_name, a_range, r_name)

    notify_telegram(f"✨ تم النشر بنجاح!\nسورة {s_name} ({a_range})\nالرابط: {pub_url}")
    print("=== اكتمل النشر بنجاح ===", flush=True)

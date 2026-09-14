import os
import sys
import json
import random
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip

# آيات قصيرة شديدة التأثير والسكينة (نفس نمط الفيديوهات المليونية)
VIRAL_AYAT = [
    {"surah": 13, "start": 28, "end": 28, "name": "الرعد"},     # ألا بذكر الله تطمئن القلوب
    {"surah": 94, "start": 5, "end": 6, "name": "الشرح"},       # فإن مع العسر يسرا
    {"surah": 20, "start": 46, "end": 46, "name": "طه"},        # إنني معكما أسمع وأرى
    {"surah": 6, "start": 15, "end": 15, "name": "الأنعام"},     # قل إني أخاف إن عصيت ربي
    {"surah": 2, "start": 186, "end": 186, "name": "البقرة"},    # وإذا سألك عبادي عني فإني قريب
    {"surah": 65, "start": 3, "end": 3, "name": "الطلاق"},      # ويرزقه من حيث لا يحتسب
    {"surah": 21, "start": 87, "end": 87, "name": "الأنبياء"},   # لا إله إلا أنت سبحانك إني كنت من الظالمين
    {"surah": 93, "start": 3, "end": 5, "name": "الضحى"},       # ما ودعك ربك وما قلى
    {"surah": 39, "start": 53, "end": 53, "name": "الزمر"},      # قل يا عبادي الذين أسرفوا على أنفسهم
    {"surah": 55, "start": 13, "end": 13, "name": "الرحمن"},    # فبأي آلاء ربكما تكذبان
    {"surah": 14, "start": 34, "end": 34, "name": "إبراهيم"}     # وآتاكم من كل ما سألتموه
]

RECITERS_POOL = [
    ("ar.alafasy", "مشاري العفاسي"),
    ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد"),
    ("ar.husary", "محمود خليل الحصري"),
    ("ar.minshawi", "محمد صديق المنشاوي")
]

AMIRI_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Bold.ttf"

def ensure_quran_font():
    """تحميل خط المصحف الشريف Amiri Bold لضمان رسم الحروف والتشكيل بأعلى جودة"""
    font_path = "Amiri-Bold.ttf"
    if not os.path.exists(font_path):
        print("تحميل خط القرآن الكريم (Amiri Bold)...", flush=True)
        try:
            r = requests.get(AMIRI_FONT_URL, timeout=15)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Font download fallback: {e}", flush=True)
    return font_path if os.path.exists(font_path) else None

def get_ayah_data(surah_num, start_ayah, end_ayah, reciter_id, reciter_name):
    print(f"جلب الآيات سورة {surah_num} ({start_ayah}-{end_ayah})...", flush=True)
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    meta_res = requests.get(meta_url, timeout=15).json()
    surah_name = meta_res.get("data", {}).get("name", f"سورة {surah_num}")

    verses = []
    audio_urls = []

    for a_num in range(start_ayah, end_ayah + 1):
        ayah_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/{reciter_id}"
        try:
            res = requests.get(ayah_url, timeout=15).json()
            if res.get("status") == "OK" and "data" in res:
                verses.append(res["data"].get("text", "").strip())
                a_link = res["data"].get("audio")
                if not a_link:
                    fb = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/ar.alafasy", timeout=15).json()
                    a_link = fb.get("data", {}).get("audio")
                if a_link:
                    audio_urls.append(a_link)
        except Exception as e:
            print(f"Audio fetch error: {e}", flush=True)

    if not audio_urls:
        raise ValueError("تعذر تحميل التلاوة الصوتية.")

    with open("recitation.mp3", "wb") as f:
        for url in audio_urls:
            f.write(requests.get(url, timeout=25).content)

    full_arabic = " ۝ ".join(verses) + " ۝"
    ayah_range = f"{start_ayah}-{end_ayah}" if start_ayah != end_ayah else f"{start_ayah}"
    return full_arabic, surah_name, ayah_range, reciter_name

def download_majestic_nature_video():
    """تنزيل مشاهد جبال وطبيعة ساحرة تشبه لقطات سويسرا والنرويج تماماً"""
    print("تنزيل خلفية طبيعية سينمائية فائقة الجودة من Pexels...", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}

    queries = [
        "switzerland mountains drone vertical",
        "alps landscape sunny green valley",
        "scenic mountains clouds aerial",
        "norway mountains drone vertical",
        "breathtaking nature aerial mountains valley",
        "green mountains landscape vertical 4k"
    ]
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"

    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        videos = res.get("videos", [])
        if videos:
            chosen = random.choice(videos)
            # اختيار أعلى جودة عمودية متاحة
            video_files = sorted(chosen["video_files"], key=lambda x: x.get("width", 0))
            best_link = video_files[-1]["link"]
            v_data = requests.get(best_link, timeout=35).content
            with open("bg_video.mp4", "wb") as f:
                f.write(v_data)
            return "bg_video.mp4"
    except Exception as e:
        print(f"Pexels warning: {e}", flush=True)

    return "bg_video.mp4"

def generate_quran_text_overlay(arabic_text, target_width=1080, target_height=1920):
    """توليد صورة شفافة بالآية القرآنية في المنتصف مع التشكيل والظل عبر Pillow"""
    font_file = ensure_quran_font()

    img = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # تقسيم الآية لأسطر مريحة للعين (3 إلى 4 كلمات في السطر)
    words = arabic_text.split()
    words_per_line = 3 if len(words) <= 6 else 4
    lines = []
    for i in range(0, len(words), words_per_line):
        chunk = " ".join(words[i:i + words_per_line])
        # تشبيك الحروف وتطبيق الاتجاه العربي لكل سطر
        reshaped = arabic_reshaper.reshape(chunk)
        lines.append(get_display(reshaped))

    formatted_multiline = "\n".join(lines)

    # حجم الخط حسب عدد الكلمات
    if len(words) <= 5:
        font_size = 72
    elif len(words) <= 10:
        font_size = 62
    else:
        font_size = 52

    if font_file:
        font = ImageFont.truetype(font_file, font_size)
    else:
        font = ImageFont.load_default()

    center_x = target_width // 2
    center_y = target_height // 2

    # رسم ظل أسود خفيف ناعم لضمان القراءة بوضوح
    for offset_x, offset_y in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
        draw.multiline_text(
            (center_x + offset_x, center_y + offset_y),
            formatted_multiline,
            font=font,
            fill=(0, 0, 0, 220),
            align="center",
            anchor="mm",
            spacing=25
        )

    # رسم النص الأبيض الناصع
    draw.multiline_text(
        (center_x, center_y),
        formatted_multiline,
        font=font,
        fill=(255, 255, 255, 255),
        align="center",
        anchor="mm",
        spacing=25
    )

    overlay_path = "quran_overlay.png"
    img.save(overlay_path, "PNG")
    return overlay_path

def build_viral_aesthetic_reel(arabic_text):
    print("مونتاج الفيديو بالنمط القرآني النقي 100%...", flush=True)
    audio_clip = AudioFileClip("recitation.mp3")
    audio_duration = audio_clip.duration + 1.0

    video_clip = VideoFileClip("bg_video.mp4")
    if video_clip.duration < audio_duration:
        video_clip = video_clip.loop(duration=audio_duration)
    else:
        video_clip = video_clip.subclip(0, audio_duration)

    video_clip = video_clip.resize((1080, 1920))

    # إنشاء طبقة النص القرآني كصورة شفافة مدمجة
    overlay_img_path = generate_quran_text_overlay(arabic_text)
    txt_clip = ImageClip(overlay_img_path).set_duration(audio_duration)

    final = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)

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

def post_to_tiktok_via_buffer(video_url, surah_name, ayah_range, reciter_name):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        print("بيانات Buffer غير مكتملة، تم تخطي النشر.", flush=True)
        return

    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]

    caption = (
        f"سورة {surah_name} 🤍 (الآية {ayah_range})\n"
        f"القارئ: {reciter_name}\n\n"
        f"أرح قلبك ومسمعك بآيات الله 🌿\n\n"
        f"#قرآن #تلاوة_خاشعة #راحة_نفسية #سورة_{surah_name.replace(' ', '_')} "
        f"#{reciter_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )
    video_title = f"سورة {surah_name} ({ayah_range}) | تلاوة خاشعة بصوت {reciter_name}"

    graphql_url = "https://api.buffer.com"
    headers = {
        "Authorization": f"Bearer {buffer_token}",
        "Content-Type": "application/json"
    }

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
            "assets": [
                {
                    "video": {
                        "url": video_url
                    }
                }
            ]
        }

        if service == "youtube" or ch_id == "6aa72b30ea19ca0bde39598b":
            post_input["metadata"] = {
                "youtube": {
                    "title": video_title[:100],
                    "categoryId": "27"
                }
            }
        elif service == "instagram" or ch_id == "6aa6d1fbea19ca0bde35e91c":
            post_input["metadata"] = {
                "instagram": {
                    "type": "reel",
                    "shouldShareToFeed": True
                }
            }

        try:
            res = requests.post(
                graphql_url,
                headers=headers,
                json={"query": mutation, "variables": {"input": post_input}},
                timeout=30
            )
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
    print("=== بدء إنتاج فيديو القرآن السينمائي النقي (Viral Style) ===", flush=True)
    item = random.choice(VIRAL_AYAT)
    rec = random.choice(RECITERS_POOL)

    notify_telegram(f"🎬 جاري إنتاج ريلز سينمائي:\nسورة {item['name']} ({item['start']}) بصوت {rec[1]}...")

    ar_text, s_name, a_range, r_name = get_ayah_data(
        item["surah"], item["start"], item["end"], rec[0], rec[1]
    )

    download_majestic_nature_video()
    build_viral_aesthetic_reel(ar_text)
    pub_url = upload_video_to_github_release()

    post_to_tiktok_via_buffer(pub_url, s_name, a_range, r_name)

    notify_telegram(f"✨ تم النشر بنجاح على جميع القنوات!\nسورة {s_name} ({a_range})\nالرابط: {pub_url}")
    print("=== اكتمل النشر التلقائي بنجاح ===", flush=True)

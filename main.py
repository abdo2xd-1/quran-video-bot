import os
import sys
import json
import random
import textwrap
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, 
    CompositeVideoClip, ColorClip
)

# باقة منتقاة من أوقع الآيات القرآنية القصيرة والمهدئة للقلوب المناسبة للمشاهد المليونية
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
]

RECITERS_POOL = [
    ("ar.alafasy", "مشاري العفاسي"),
    ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد"),
    ("ar.husary", "محمود خليل الحصري"),
    ("ar.minshawi", "محمد صديق المنشاوي")
]

def format_arabic_text(text):
    """ضبط اتجاه وتشكيل الخط العربي"""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def wrap_arabic_verses(text, words_per_line=4):
    """توزيع كلمات الآية على أسطر متناسقة في منتصف الشاشة"""
    words = text.split()
    lines = []
    for i in range(0, len(words), words_per_line):
        chunk = " ".join(words[i:i + words_per_line])
        lines.append(format_arabic_text(chunk))
    return "\n".join(lines)

def get_ayah_audio_and_text(surah_num, start_ayah, end_ayah, reciter_id, reciter_name):
    print(f"جلب الآيات {surah_num}:{start_ayah}-{end_ayah}...", flush=True)
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

def download_person_in_nature_video():
    """جلب فيديو سينمائي لأشخاص يتأملون أو يمشون وسط الطبيعة والجبال"""
    print("تنزيل خلفية لشخص في الطبيعة السينمائية...", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}

    # استعلامات دقيقة لمحاكاة الفيديوهات الرائجة في الصور
    queries = [
        "man walking mountains cinematic",
        "person sitting mountains view",
        "traveler looking at nature valley",
        "person looking at mountains sunset",
        "solitary person hiking foggy mountains",
        "person walking nature moody road",
        "man looking at mountain landscape"
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
            v_data = requests.get(best_link, timeout=35).content
            with open("bg_video.mp4", "wb") as f:
                f.write(v_data)
            return "bg_video.mp4"
    except Exception as e:
        print(f"Pexels warning: {e}", flush=True)

    return "bg_video.mp4"

def build_viral_aesthetic_reel(arabic_text):
    print("مونتاج الفيديو بالنمط السينمائي الصافي...", flush=True)
    audio_clip = AudioFileClip("recitation.mp3")
    audio_duration = audio_clip.duration + 1.0

    video_clip = VideoFileClip("bg_video.mp4")
    if video_clip.duration < audio_duration:
        video_clip = video_clip.loop(duration=audio_duration)
    else:
        video_clip = video_clip.subclip(0, audio_duration)

    video_clip = video_clip.resize((1080, 1920))

    # اختيار خط عربي أصيل للقرآن
    font_path = "DejaVu-Sans"
    if os.path.exists("/usr/share/fonts/truetype/scheherazade/Scheherazade-Regular.ttf"):
        font_path = "/usr/share/fonts/truetype/scheherazade/Scheherazade-Regular.ttf"
    elif os.path.exists("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"):
        font_path = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"

    # تدرج خفيف وناعم جداً للحفاظ على جمال ووضوح ألوان الفيديو الطبيعي
    dim_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.25).set_duration(audio_duration)

    # ضبط حجم الخط حسب طول الآية المختارة
    word_count = len(arabic_text.split())
    if word_count <= 6:
        font_size = 54
        w_per_line = 3
    elif word_count <= 14:
        font_size = 46
        w_per_line = 4
    else:
        font_size = 38
        w_per_line = 5

    formatted_text = wrap_arabic_verses(arabic_text, words_per_line=w_per_line)

    # النص في منتصف الشاشة مع حدود وظل أسود ناعم ليبرز بوضوح فائق كما في الصورة
    quran_clip = TextClip(
        formatted_text,
        fontsize=font_size,
        color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=2,
        font=font_path,
        method="label",
        align="center"
    ).set_duration(audio_duration).set_position(("center", "center"))

    final = CompositeVideoClip([video_clip, dim_overlay, quran_clip]).set_audio(audio_clip)

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

        # متطلبات يوتيوب وإنستغرام المعتمدة
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
    print("=== بدء إنتاج فيديو القرآن السينمائي (Aesthetic Clean) ===", flush=True)
    item = random.choice(VIRAL_AYAT)
    rec = random.choice(RECITERS_POOL)

    notify_telegram(f"🎬 جاري إنتاج ريلز سينمائي نقي:\nسورة {item['name']} ({item['start']}) بصوت {rec[1]}...")

    ar_text, s_name, a_range, r_name = get_ayah_audio_and_text(
        item["surah"], item["start"], item["end"], rec[0], rec[1]
    )

    download_person_in_nature_video()
    build_viral_aesthetic_reel(ar_text)
    pub_url = upload_video_to_github_release()

    post_to_tiktok_via_buffer(pub_url, s_name, a_range, r_name)

    notify_telegram(f"✨ تم النشر بنجاح على جميع الحسابات!\nسورة {s_name} ({a_range})\nالرابط: {pub_url}")
    print("=== اكتمل النشر التلقائي بنجاح ===", flush=True)

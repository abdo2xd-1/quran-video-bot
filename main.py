import os
import sys
import json
import random
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

AUTO_CONTENT = [
    {"surah": 1, "start": 1, "end": 7, "name": "الفاتحة"},
    {"surah": 93, "start": 1, "end": 11, "name": "الضحى"},
    {"surah": 94, "start": 1, "end": 8, "name": "الشرح"},
    {"surah": 95, "start": 1, "end": 8, "name": "التين"},
    {"surah": 97, "start": 1, "end": 5, "name": "القدر"},
    {"surah": 103, "start": 1, "end": 3, "name": "العصر"},
    {"surah": 108, "start": 1, "end": 3, "name": "الكوثر"},
    {"surah": 112, "start": 1, "end": 4, "name": "الإخلاص"},
    {"surah": 113, "start": 1, "end": 5, "name": "الفلق"},
    {"surah": 114, "start": 1, "end": 6, "name": "الناس"},
    {"surah": 67, "start": 1, "end": 5, "name": "الملك"},
    {"surah": 55, "start": 1, "end": 8, "name": "الرحمن"}
]

RECITERS_POOL = [
    ("ar.alafasy", "مشاري العفاسي"),
    ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد"),
    ("ar.husary", "محمود خليل الحصري"),
    ("ar.minshawi", "محمد صديق المنشاوي")
]

def format_arabic_text(text):
    """تشبيك الحروف وضبط اتجاه الكتابة العربية"""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def get_custom_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id="ar.alafasy", reciter_name="العفاسي"):
    print(f"جلب آيات سورة {surah_num} ({start_ayah}-{end_ayah})...", flush=True)
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    meta_res = requests.get(meta_url, timeout=15).json()
    surah_name = meta_res.get("data", {}).get("name", f"سورة {surah_num}")

    verses_text = []
    audio_urls = []

    for a_num in range(start_ayah, end_ayah + 1):
        ayah_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/{reciter_id}"
        try:
            a_res = requests.get(ayah_url, timeout=15).json()
            if a_res.get("status") == "OK" and "data" in a_res:
                data = a_res["data"]
                verses_text.append(data.get("text", ""))
                audio_link = data.get("audio")
                if not audio_link:
                    fallback_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/ar.alafasy"
                    fb_res = requests.get(fallback_url, timeout=15).json()
                    audio_link = fb_res.get("data", {}).get("audio")
                if audio_link:
                    audio_urls.append(audio_link)
        except Exception as e:
            print(f"Error fetching ayah {a_num}: {e}", flush=True)

    if not audio_urls:
        raise ValueError("فشل في جلب المقاطع الصوتية للآيات المحددة.")

    with open("recitation.mp3", "wb") as f_out:
        for url in audio_urls:
            r = requests.get(url, timeout=20)
            f_out.write(r.content)

    full_text = " ۝ ".join(verses_text) + " ۝"
    ayah_range = f"{start_ayah}-{end_ayah}"
    is_friday = (surah_num == 18)

    return full_text, surah_name, ayah_range, reciter_name, is_friday

def download_aesthetic_background():
    print("تنزيل خلفية سينمائية من Pexels...", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    
    queries = ["nature rain dark", "forest mist aesthetic", "ocean waves dark", "clouds starry sky"]
    query = random.choice(queries)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"
    
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        videos = res.get("videos", [])
        if videos:
            chosen = random.choice(videos)
            video_files = sorted(chosen["video_files"], key=lambda x: x.get("width", 0))
            best_link = video_files[-1]["link"]
            v_data = requests.get(best_link, timeout=30).content
            with open("bg_video.mp4", "wb") as f:
                f.write(v_data)
            return "bg_video.mp4"
    except Exception as e:
        print(f"Pexels warning: {e}", flush=True)

    return "bg_video.mp4"

def build_aesthetic_quran_video(quran_text):
    print("مونتاج الفيديو بدقة 1080x1920...", flush=True)
    audio_clip = AudioFileClip("recitation.mp3")
    audio_duration = audio_clip.duration + 1.5

    video_clip = VideoFileClip("bg_video.mp4")
    if video_clip.duration < audio_duration:
        video_clip = video_clip.loop(duration=audio_duration)
    else:
        video_clip = video_clip.subclip(0, audio_duration)

    video_clip = video_clip.resize((1080, 1920))

    font_name = "DejaVu-Sans"
    if os.path.exists("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"):
        font_name = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
    elif os.path.exists("/usr/share/fonts/truetype/scheherazade/Scheherazade-Regular.ttf"):
        font_name = "/usr/share/fonts/truetype/scheherazade/Scheherazade-Regular.ttf"

    proper_quran_text = format_arabic_text(quran_text)

    # حساب حجم الخط ديناميكياً لتفادي تجاوز حدود ImageMagick
    text_length = len(proper_quran_text)
    if text_length > 600:
        calculated_fontsize = 26
    elif text_length > 400:
        calculated_fontsize = 30
    elif text_length > 200:
        calculated_fontsize = 34
    else:
        calculated_fontsize = 40

    txt_clip = TextClip(
        proper_quran_text,
        fontsize=calculated_fontsize,
        color="white",
        font=font_name,
        method="caption",
        size=(860, 1400),
        align="center"
    ).set_duration(audio_duration).set_position(("center", "center"))

    final = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)
    final.write_videofile(
        "final_reel.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="2500k",
        threads=4,
        preset="ultrafast"
    )
    return "final_reel.mp4"

def upload_video_to_github_release():
    print("رفع الفيديو إلى GitHub Releases...", flush=True)
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    tag_name = f"video-{int(random.random()*1000000000)}"

    create_url = f"https://api.github.com/repos/{repo}/releases"
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    rel_data = {
        "tag_name": tag_name,
        "name": f"Reel Release {tag_name}",
        "draft": False,
        "prerelease": False
    }
    res = requests.post(create_url, headers=headers, json=rel_data, timeout=20).json()
    upload_url = res["upload_url"].split("{")[0]

    with open("final_reel.mp4", "rb") as f:
        up_headers = {
            "Authorization": f"token {gh_token}",
            "Content-Type": "video/mp4"
        }
        up_res = requests.post(
            f"{upload_url}?name=final_reel.mp4",
            headers=up_headers,
            data=f,
            timeout=60
        ).json()

    return up_res.get("browser_download_url")

def post_to_tiktok_via_buffer(video_url, surah_name, ayah_range, reciter_name, is_friday=False):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        print("بيانات Buffer غير مكتملة، تم تخطي النشر.", flush=True)
        return

    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]

    caption = (
        f"سورة {surah_name} 🤍 (الآيات {ayah_range})\n"
        f"القارئ: {reciter_name}\n\n"
        f"أرح مسمعك وقلبك بآيات الله 🌿\n\n"
        f"#قرآن #تلاوات_خاشعة #راحة_نفسية #سورة_{surah_name.replace(' ', '_')} "
        f"#{reciter_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )

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
      }
    }
    """

    for ch_id in channel_ids:
        # بنية attachments المعتمدة في Buffer GraphQL لملفات الفيديو
        variables = {
            "input": {
                "channelId": ch_id,
                "text": caption,
                "mode": "shareNow",
                "schedulingType": "automatic",
                "attachments": {
                    "videos": [video_url]
                }
            }
        }
        try:
            res = requests.post(
                graphql_url,
                headers=headers,
                json={"query": mutation, "variables": variables},
                timeout=30
            )
            data = res.json()
            if "errors" in data and data["errors"]:
                print(f"⚠️ تفاصيل رد القناة {ch_id}: {data['errors'][0].get('message', data['errors'])}", flush=True)
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
    print("=== بدء النشر التلقائي للساعة الحالية ===", flush=True)
    item = random.choice(AUTO_CONTENT)
    rec = random.choice(RECITERS_POOL)
    
    notify_telegram(f"⏰ بدء إنتاج فيديو الساعة التلقائي:\nسورة {item['name']} بصوت {rec[1]}...")
    
    v_text, s_name, a_range, r_name, is_fri = get_custom_ayahs_data(
        item["surah"], item["start"], item["end"], rec[0], rec[1]
    )
    download_aesthetic_background()
    build_aesthetic_quran_video(v_text)
    pub_url = upload_video_to_github_release()
    post_to_tiktok_via_buffer(pub_url, s_name, a_range, r_name, is_fri)
    
    notify_telegram(f"✅ اكتمل نشر فيديو الساعة بنجاح!\nسورة {s_name} ({a_range})\nالرابط: {pub_url}")
    print("=== اكتمل النشر التلقائي بنجاح ===", flush=True)

import os
import sys
import json
import random
import datetime
import requests
import arabic_reshaper
from bidi.algorithm import get_display
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, 
    CompositeVideoClip, ColorClip
)

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
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def select_contextual_surah():
    """اختيار السورة بذكاء حسب اليوم والوقت (الكهف يوم الجمعة، الملك بالليل)"""
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=2)  # توقيت القاهرة
    is_friday = (now.weekday() == 4)
    is_night = (now.hour >= 21 or now.hour <= 4)

    if is_friday and 6 <= now.hour <= 17:
        print("🕌 توقيت الجمعة: اختيار سورة الكهف...", flush=True)
        return {"surah": 18, "start": 1, "end": 4, "name": "الكهف"}, True
    elif is_night:
        print("🌙 توقيت المساء: اختيار سورة الملك...", flush=True)
        return {"surah": 67, "start": 1, "end": 5, "name": "الملك"}, False
    else:
        return random.choice(AUTO_CONTENT), False

def get_custom_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id="ar.alafasy", reciter_name="العفاسي"):
    print(f"جلب آيات وترجمة سورة {surah_num} ({start_ayah}-{end_ayah})...", flush=True)
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    meta_res = requests.get(meta_url, timeout=15).json()
    surah_name = meta_res.get("data", {}).get("name", f"سورة {surah_num}")

    verses_arabic = []
    verses_english = []
    audio_urls = []

    for a_num in range(start_ayah, end_ayah + 1):
        # الآية بالصوت العربي
        ayah_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/{reciter_id}"
        # الترجمة الإنجليزية
        eng_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/en.sahih"

        try:
            a_res = requests.get(ayah_url, timeout=15).json()
            if a_res.get("status") == "OK" and "data" in a_res:
                data = a_res["data"]
                verses_arabic.append(data.get("text", ""))
                audio_link = data.get("audio")
                if not audio_link:
                    fallback_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/ar.alafasy"
                    fb_res = requests.get(fallback_url, timeout=15).json()
                    audio_link = fb_res.get("data", {}).get("audio")
                if audio_link:
                    audio_urls.append(audio_link)

            eng_res = requests.get(eng_url, timeout=15).json()
            if eng_res.get("status") == "OK" and "data" in eng_res:
                verses_english.append(eng_res["data"].get("text", ""))
        except Exception as e:
            print(f"Error fetching ayah {a_num}: {e}", flush=True)

    if not audio_urls:
        raise ValueError("فشل في جلب المقاطع الصوتية.")

    with open("recitation.mp3", "wb") as f_out:
        for url in audio_urls:
            r = requests.get(url, timeout=20)
            f_out.write(r.content)

    full_arabic = " ۝ ".join(verses_arabic) + " ۝"
    full_english = " ".join(verses_english)
    ayah_range = f"{start_ayah}-{end_ayah}"

    return full_arabic, full_english, surah_name, ayah_range, reciter_name

def download_aesthetic_background():
    print("تنزيل خلفية سينمائية من Pexels...", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    
    queries = ["nature rain dark aesthetic", "forest mist calm", "ocean waves dark moody", "starry night sky clouds"]
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

def build_aesthetic_quran_video(arabic_text, english_text, surah_name, ayah_range, reciter_name):
    print("مونتاج الفيديو بالترجمة والقناع السينمائي...", flush=True)
    audio_clip = AudioFileClip("recitation.mp3")
    audio_duration = audio_clip.duration + 1.2

    video_clip = VideoFileClip("bg_video.mp4")
    if video_clip.duration < audio_duration:
        video_clip = video_clip.loop(duration=audio_duration)
    else:
        video_clip = video_clip.subclip(0, audio_duration)

    video_clip = video_clip.resize((1080, 1920))

    font_arabic = "DejaVu-Sans"
    if os.path.exists("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"):
        font_arabic = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
    elif os.path.exists("/usr/share/fonts/truetype/scheherazade/Scheherazade-Regular.ttf"):
        font_arabic = "/usr/share/fonts/truetype/scheherazade/Scheherazade-Regular.ttf"

    font_eng = "DejaVu-Sans"

    # 1. قناع تباين داكن فوق الفيديو لضمان وضوح النصوص
    overlay_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.38).set_duration(audio_duration)

    # 2. شريط علوي أنيق (اسم السورة والقارئ)
    badge_text = format_arabic_text(f"{surah_name} ۞ {reciter_name}")
    header_clip = TextClip(
        badge_text,
        fontsize=32,
        color="#F3F4F6",
        font=font_arabic,
        method="caption",
        size=(900, 80),
        align="center"
    ).set_duration(audio_duration).set_position(("center", 200))

    # 3. النص القرآني العربي
    proper_quran = format_arabic_text(arabic_text)
    text_len = len(proper_quran)
    ar_fontsize = 26 if text_len > 550 else (30 if text_len > 350 else 36)

    arabic_clip = TextClip(
        proper_quran,
        fontsize=ar_fontsize,
        color="#FFFFFF",
        font=font_arabic,
        method="caption",
        size=(880, 800),
        align="center"
    ).set_duration(audio_duration).set_position(("center", 620))

    # 4. الترجمة الإنجليزية بخط فرعي أنيق
    eng_fontsize = 20 if len(english_text) > 400 else 23
    english_clip = TextClip(
        f'"{english_text}"',
        fontsize=eng_fontsize,
        color="#D1D5DB",
        font=font_eng,
        method="caption",
        size=(840, 360),
        align="center"
    ).set_duration(audio_duration).set_position(("center", 1450))

    final = CompositeVideoClip(
        [video_clip, overlay_clip, header_clip, arabic_clip, english_clip]
    ).set_audio(audio_clip)

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
    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    rel_data = {"tag_name": tag_name, "name": f"Reel Release {tag_name}", "draft": False, "prerelease": False}
    res = requests.post(create_url, headers=headers, json=rel_data, timeout=20).json()
    upload_url = res["upload_url"].split("{")[0]

    with open("final_reel.mp4", "rb") as f:
        up_headers = {"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}
        up_res = requests.post(f"{upload_url}?name=final_reel.mp4", headers=up_headers, data=f, timeout=60).json()

    return up_res.get("browser_download_url")

def generate_ai_caption(surah_name, ayah_range, reciter_name, arabic_text):
    """توليد تدبر قصير ومؤثر وسؤال تفاعلي بالذكاء الاصطناعي عبر Groq"""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    default_caption = (
        f"سورة {surah_name} 🤍 (الآيات {ayah_range})\n"
        f"القارئ: {reciter_name}\n\n"
        f"أرح مسمعك وقلبك بآيات الله 🌿\n\n"
        f"#قرآن #تلاوات_خاشعة #سورة_{surah_name.replace(' ', '_')} "
        f"#{reciter_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )

    if not groq_key:
        return default_caption

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        prompt = (
            f"اكتب كابشن جذاب ومؤثر لإنستغرام وتيك توك لتلاوة سورة {surah_name} الآيات ({ayah_range}) بصوت {reciter_name}.\n"
            f"مقتطف من الآيات: {arabic_text[:150]}\n"
            f"المطلوب بدقة وبدون أي مقدمات:\n"
            f"1. سطرين تدبر إيماني هادئ ومؤثر.\n"
            f"2. سؤال تفاعلي بسيط في النهاية يدعو للتأمل ومشاركة الأجر في التعليقات.\n"
            f"3. 6 هاشتاقات عربية وإنجليزية قوية عن القرآن والتلاوة.\n"
            f"اكتب المنشور مباشرة دون أي تمهيد."
        )
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq caption generation fallback: {e}", flush=True)
        return default_caption

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

def post_to_tiktok_via_buffer(video_url, surah_name, ayah_range, reciter_name, caption):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        print("بيانات Buffer غير مكتملة، تم تخطي النشر.", flush=True)
        return

    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
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
    print("=== بدء إنتاج ونشر فيديو القرآن المطور ===", flush=True)
    item, is_special = select_contextual_surah()
    rec = random.choice(RECITERS_POOL)
    
    notify_telegram(f"🎬 جاري تجهيز فيديو سينمائي:\nسورة {item['name']} بصوت {rec[1]} مع الترجمة الإنجليزية...")

    ar_text, en_text, s_name, a_range, r_name = get_custom_ayahs_data(
        item["surah"], item["start"], item["end"], rec[0], rec[1]
    )

    download_aesthetic_background()
    build_aesthetic_quran_video(ar_text, en_text, s_name, a_range, r_name)
    pub_url = upload_video_to_github_release()

    # توليد الكابشن التفاعلي عبر الذكاء الاصطناعي
    ai_caption = generate_ai_caption(s_name, a_range, r_name, ar_text)

    post_to_tiktok_via_buffer(pub_url, s_name, a_range, r_name, ai_caption)

    notify_telegram(f"✨ تم النشر السينمائي بنجاح!\nسورة {s_name} ({a_range})\nالرابط: {pub_url}\n\nالكابشن المستخدم:\n{ai_caption[:180]}...")
    print("=== اكتمل خط الإنتاج بنجاح ===", flush=True)

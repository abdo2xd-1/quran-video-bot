import os
import sys
import json
import base64
import random
import shutil
import subprocess
import requests
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips
)

# قائمة السور والمقاطع (من 3 آيات كحد أدنى إلى سورة كاملة)
QURAN_PLAYLIST = [
    {"surah": 108, "start": 1, "end": 3, "name": "الكوثر"},
    {"surah": 103, "start": 1, "end": 3, "name": "العصر"},
    {"surah": 112, "start": 1, "end": 4, "name": "الإخلاص"},
    {"surah": 113, "start": 1, "end": 5, "name": "الفلق"},
    {"surah": 114, "start": 1, "end": 6, "name": "الناس"},
    {"surah": 97,  "start": 1, "end": 5, "name": "القدر"},
    {"surah": 94,  "start": 1, "end": 8, "name": "الشرح"},
    {"surah": 95,  "start": 1, "end": 8, "name": "التين"},
    {"surah": 1,   "start": 1, "end": 7, "name": "الفاتحة"},
    {"surah": 67,  "start": 1, "end": 4, "name": "الملك"},
    {"surah": 55,  "start": 1, "end": 5, "name": "الرحمن"},
    {"surah": 93,  "start": 1, "end": 5, "name": "الضحى"}
]

RECITERS_POOL = [
    ("ar.alafasy", "مشاري العفاسي"),
    ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد"),
    ("ar.husary", "محمود خليل الحصري"),
    ("ar.minshawi", "محمد صديق المنشاوي")
]

THEMATIC_SERIES = {
    "سكينة": {
        "tag": "#سلسلة_سكينة_القلب",
        "playlist": "سكينة وهدوء القلب",
        "hooks": [
            "تلاوة تريح القلب وتزيل الهم والضيق 🌿",
            "أرح مسمعك ونفسك بآيات الله والسكينة 🤍",
            "سكينة تغمر الروح وهدوء للبال 🕊️"
        ]
    },
    "نوم": {
        "tag": "#سلسلة_تلاوات_النوم",
        "playlist": "رفيق النوم والسكينة",
        "hooks": [
            "أنزل السكينة على روحك قبل أن تنام 🌙",
            "تلاوة هادئة تعينك على نوم عميق ومطمئن 🕊️",
            "أرح سمعك وقلبك قبل المنام بآيات الله 🤍"
        ]
    },
    "قصار": {
        "tag": "#سلسلة_قصار_السور",
        "playlist": "قصار السور كاملة",
        "hooks": [
            "دقيقة من الطمأنينة لا تفوتها 🤍",
            "استمع بقلبك لقصار السور بتلاوة خاشعة 🌿",
            "تلاوة مباركة تملأ يومك بالبركة والراحة 🕊️"
        ]
    },
    "فجر": {
        "tag": "#سلسلة_آيات_الفجر",
        "playlist": "آيات الفجر والبركة",
        "hooks": [
            "بداية يوم مطمئنة ومباركة بآيات الله 🕊️",
            "آيات تفتح لك أبواب الرزق والطمأنينة مع الفجر 🌿"
        ]
    }
}

PINNED_COMMENTS = [
    "اكتب شيئاً تؤجر عليه في ميزان حسناتك 🌿 (سبحان الله، الحمد لله، لا إله إلا الله، الله أكبر) 🤍",
    "شارك الآية لعلها تريح قلباً متعباً الآن وتكون لك صدقة جارية يوم القيامة 🕊️",
    "ما هي أكثر آية تشعرك بالسكينة والطمأنينة عندما تسمعها؟ شاركنا بها في التعليقات 🤍",
    "اللهم اجعل القرآن الكريم ربيع قلوبنا، ونور صدورنا، وجلاء أحزاننا وذهاب همومنا 🤲"
]

FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

def build_seo_metadata(surah_name, ayah_range, reciter_name, surah_num):
    if surah_num == 67:
        theme = THEMATIC_SERIES["نوم"]
        intent_title = f"تلاوة للنوم العميق وراحة القلب 🌙 سورة {surah_name} ({ayah_range}) بصوت {reciter_name}"
    elif surah_num == 93:
        theme = THEMATIC_SERIES["فجر"]
        intent_title = f"آيات تفتح لك أبواب الخير والرزق 🕊️ سورة {surah_name} بصوت {reciter_name}"
    elif surah_num in [1, 94, 55]:
        theme = THEMATIC_SERIES["سكينة"]
        intent_title = f"تلاوة تريح القلب وتزيل الهم 🌿 سورة {surah_name} كاملة | {reciter_name}"
    else:
        theme = THEMATIC_SERIES["قصار"]
        intent_title = f"قصار السور لراحة البال 🤍 سورة {surah_name} كاملة | القارئ {reciter_name}"

    hook = random.choice(theme["hooks"])
    caption = (
        f"{hook}\n\n"
        f"📖 سورة {surah_name} ({ayah_range})\n"
        f"🎙️ القارئ: {reciter_name}\n"
        f"📁 {theme['playlist']}\n\n"
        f"شاركها لعلها تريح قلباً متعباً وتكون لك صدقة جارية 🤍\n\n"
        f"{theme['tag']} #تلاوة_تريح_القلب #راحة_نفسية #قرآن #سورة_{surah_name.replace(' ', '_')} "
        f"#quran #islamic_reels #fyp #explore #shorts"
    )
    return intent_title[:100], caption

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

def fetch_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id, reciter_name):
    print(f"جلب آيات سورة {surah_num} ({start_ayah}-{end_ayah})...", flush=True)
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    surah_name = requests.get(meta_url, timeout=15).json().get("data", {}).get("name", f"سورة {surah_num}")

    ayahs_list = []

    for a_num in range(start_ayah, end_ayah + 1):
        text_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/quran-simple"
        audio_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/{reciter_id}"

        t_res = requests.get(text_url, timeout=15).json()
        a_res = requests.get(audio_url, timeout=15).json()

        cleaned_text = clean_arabic_text(t_res.get("data", {}).get("text", ""))

        if a_num == 1 and surah_num != 1:
            cleaned_text = cleaned_text.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        audio_link = a_res.get("data", {}).get("audio")
        if not audio_link:
            fb = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/ar.alafasy", timeout=15).json()
            audio_link = fb.get("data", {}).get("audio")

        audio_filename = f"audio_{a_num}.mp3"
        with open(audio_filename, "wb") as f:
            f.write(requests.get(audio_link, timeout=25).content)

        ayahs_list.append({
            "number": a_num,
            "text": cleaned_text,
            "audio_path": audio_filename
        })

    ayah_range = f"{start_ayah}-{end_ayah}" if start_ayah != end_ayah else f"{start_ayah}"
    return ayahs_list, surah_name, ayah_range, reciter_name

def download_scenic_nature_video():
    print("تنزيل خلفية طبيعة سينمائية من Pexels...", flush=True)
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

def render_quran_ayah_image(text, index, font_b64, watermark_handle):
    chrome_bin = get_chrome_path()

    words_count = len(text.split())
    if words_count <= 5:
        font_size = 72
    elif words_count <= 12:
        font_size = 62
    elif words_count <= 20:
        font_size = 52
    else:
        font_size = 44

    html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
  @font-face {{
    font-family: 'AmiriQuran';
    src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype');
  }}
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  body {{
    width: 1080px;
    height: 1920px;
    background-color: rgba(0, 0, 0, 0);
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    position: relative;
  }}
  .ayah-text {{
    direction: rtl;
    text-align: center;
    font-family: 'AmiriQuran', serif;
    font-size: {font_size}px;
    font-weight: bold;
    color: #ffffff;
    line-height: 1.85;
    max-width: 920px;
    text-shadow: 
      0 0 10px rgba(0, 0, 0, 0.95),
      0 4px 18px rgba(0, 0, 0, 0.9),
      0 0 30px rgba(0, 0, 0, 0.85);
  }}
  .watermark {{
    position: absolute;
    bottom: 120px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'AmiriQuran', sans-serif;
    font-size: 25px;
    color: rgba(255, 255, 255, 0.45);
    letter-spacing: 2px;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85);
    direction: ltr;
  }}
</style>
</head>
<body>
  <div class="ayah-text">{text}</div>
  <div class="watermark">{watermark_handle}</div>
</body>
</html>"""

    html_filename = f"temp_ayah_{index}.html"
    png_filename = f"ayah_overlay_{index}.png"

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    html_abs = os.path.abspath(html_filename)
    png_abs = os.path.abspath(png_filename)

    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--hide-scrollbars",
        "--window-size=1080,1920",
        "--default-background-color=00000000",
        f"--screenshot={png_abs}",
        f"file://{html_abs}"
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(html_filename):
        os.remove(html_filename)

    return png_filename

def build_synchronized_video(ayahs_list, watermark_handle):
    print("مونتاج الفيديو وإدماج العلامة المائية في Safe Zone...", flush=True)
    font_b64 = get_font_base64()

    audio_clips = []
    text_overlay_clips = []
    current_time = 0.0

    for idx, ayah in enumerate(ayahs_list):
        a_clip = AudioFileClip(ayah["audio_path"])
        duration = a_clip.duration
        audio_clips.append(a_clip)

        img_path = render_quran_ayah_image(ayah["text"], idx, font_b64, watermark_handle)
        t_clip = (
            ImageClip(img_path)
            .set_start(current_time)
            .set_duration(duration)
            .set_position(("center", "center"))
        )
        text_overlay_clips.append(t_clip)
        current_time += duration

    final_audio = concatenate_audioclips(audio_clips)
    total_duration = current_time + 0.8

    bg_clip = VideoFileClip("bg_video.mp4")
    if bg_clip.duration < total_duration:
        bg_clip = bg_clip.loop(duration=total_duration)
    else:
        bg_clip = bg_clip.subclip(0, total_duration)

    bg_clip = bg_clip.resize((1080, 1920))
    dim_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.20).set_duration(total_duration)

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

        # ضبط متطلبات كل منصة بدون firstComment لتجنب قيود الخطة المجانية
        if service == "youtube" or ch_id == "6aa72b30ea19ca0bde39598b":
            post_input["metadata"] = {"youtube": {"title": video_title, "categoryId": "27"}}
        elif service == "instagram" or ch_id == "6aa6d1fbea19ca0bde35e91c":
            post_input["metadata"] = {
                "instagram": {
                    "type": "reel",
                    "shouldShareToFeed": True
                }
            }

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
    print("=== بدء إنتاج فيديو القرآن المتزامن الاحترافي ===", flush=True)
    item = random.choice(QURAN_PLAYLIST)
    rec = random.choice(RECITERS_POOL)
    watermark_handle = os.getenv("WATERMARK_HANDLE", "@quran_reels").strip()
    selected_pinned_comment = random.choice(PINNED_COMMENTS)

    notify_telegram(f"🎬 جاري إنتاج ريلز متزامن:\nسورة {item['name']} ({item['start']}-{item['end']}) بصوت {rec[1]}...")

    ayahs, s_name, a_range, r_name = fetch_ayahs_data(
        item["surah"], item["start"], item["end"], rec[0], rec[1]
    )

    download_scenic_nature_video()
    build_synchronized_video(ayahs, watermark_handle)
    pub_url = upload_video_to_github_release()

    video_title, full_caption = build_seo_metadata(s_name, a_range, r_name, item["surah"])
    post_to_buffer(pub_url, video_title, full_caption)

    tg_report = (
        f"✨ تم النشر بنجاح على المنصات الثلاث!\n"
        f"العنوان: {video_title}\n"
        f"الرابط: {pub_url}\n\n"
        f"📌 التعليق التفاعلي للتثبيت:\n"
        f"<code>{selected_pinned_comment}</code>"
    )
    notify_telegram(tg_report)
    print("=== اكتمل خط الإنتاج بنجاح ===", flush=True)

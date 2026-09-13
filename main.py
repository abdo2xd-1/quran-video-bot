import os
import re
import sys
import time
import random
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip
)

print("Starting Quran Bot Pipeline...")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")

RECITERS = [
    {"subfolder": "Alafasy_128kbps", "name": "مشاري العفاسي"},
    {"subfolder": "Minshawy_Murattal_128kbps", "name": "محمد صديق المنشاوي"},
    {"subfolder": "Abdul_Basit_Murattal_192kbps", "name": "عبد الباسط عبد الصمد"},
    {"subfolder": "Yasser_Ad-Dussary_128kbps", "name": "ياسر الدوسري"},
    {"subfolder": "Saood_ash-Shuraym_128kbps", "name": "سعود الشريم"}
]

AESTHETIC_QUERIES = [
    "cinematic calm sea sunset vertical",
    "misty green mountains slow motion vertical",
    "foggy forest aesthetic vertical",
    "dark clouds ocean vertical",
    "calm rain cinematic vertical",
    "mecca kaaba crowd vertical",
    "desert sunset slow motion vertical"
]

def clean_quran_symbols(text):
    cleaned = re.sub(r'[\u06D6-\u06ED]', '', text)
    return cleaned.strip()

def get_ayah_data():
    print("Fetching Ayah data...")
    today = datetime.datetime.now().weekday()
    is_friday = (today == 4)
    reciter = random.choice(RECITERS)
    
    if is_friday:
        surah_number = 18
        ayah_in_surah = random.randint(1, 110)
        url = f"https://api.alquran.cloud/v1/ayah/{surah_number}:{ayah_in_surah}"
    else:
        verse_number = random.randint(1, 6236)
        url = f"https://api.alquran.cloud/v1/ayah/{verse_number}"

    res = requests.get(url).json()
    data = res["data"]

    verse_text = clean_quran_symbols(data["text"])
    surah_name = data["surah"]["name"]
    surah_num = str(data["surah"]["number"]).zfill(3)
    ayah_num = str(data["numberInSurah"]).zfill(3)

    audio_url = f"https://everyayah.com/data/{reciter['subfolder']}/{surah_num}{ayah_num}.mp3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(audio_url, headers=headers)

    if response.status_code == 200 and len(response.content) > 5000:
        with open("audio.mp3", "wb") as f:
            f.write(response.content)
    else:
        fallback_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{data['number']}.mp3"
        fallback_res = requests.get(fallback_url, headers=headers)
        with open("audio.mp3", "wb") as f:
            f.write(fallback_res.content)
        reciter["name"] = "مشاري العفاسي"

    print(f"Ayah fetched: Surah {surah_name} ({ayah_num})")
    return verse_text, surah_name, int(ayah_num), reciter["name"], is_friday

def download_aesthetic_background():
    print("Downloading background footage from Pexels...")
    headers = {"Authorization": PEXELS_API_KEY}
    query = random.choice(AESTHETIC_QUERIES)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"

    res = requests.get(url, headers=headers).json()
    video_item = random.choice(res["videos"])

    video_file = next(f for f in video_item["video_files"] if f.get("width") and f["width"] <= 1080)
    video_url = video_file["link"]

    with open("bg.mp4", "wb") as f:
        f.write(requests.get(video_url).content)
    print("Background downloaded successfully.")

def create_quran_text_image(text, width=1080, height=1920):
    print("Generating verse typography image...")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    font_file = "Amiri-Regular.ttf" if os.path.exists("Amiri-Regular.ttf") else "Arial"
    font = ImageFont.truetype(font_file, 64)

    display_text = f"﴿ {text} ﴾"

    # تقسيم الكلمات لأسطر
    words = display_text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_str = " ".join(current_line)
        try:
            bbox = draw.textbbox((0, 0), test_str, font=font, direction="rtl")
        except Exception:
            bbox = draw.textbbox((0, 0), test_str, font=font)
            
        if (bbox[2] - bbox[0]) > 860:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    final_text = "\n".join(lines)

    try:
        bbox = draw.multiline_textbbox((0, 0), final_text, font=font, direction="rtl", align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        draw.multiline_text((x+2, y+2), final_text, font=font, fill=(0, 0, 0, 220), direction="rtl", align="center")
        draw.multiline_text((x, y), final_text, font=font, fill=(255, 255, 255, 255), direction="rtl", align="center")
    except Exception:
        bbox = draw.multiline_textbbox((0, 0), final_text, font=font, align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        draw.multiline_text((x+2, y+2), final_text, font=font, fill=(0, 0, 0, 220), align="center")
        draw.multiline_text((x, y), final_text, font=font, fill=(255, 255, 255, 255), align="center")

    image.save("verse_overlay.png", "PNG")
    print("Verse image saved.")

def build_aesthetic_quran_video(verse_text):
    print("Rendering video with MoviePy...")
    audio_clip = AudioFileClip("audio.mp3")
    duration = audio_clip.duration + 1.2

    video_clip = VideoFileClip("bg.mp4").subclip(0, duration).resize((1080, 1920))
    video_clip = video_clip.set_audio(audio_clip)

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.42).set_duration(duration)

    create_quran_text_image(verse_text)
    txt_layer = ImageClip("verse_overlay.png").set_duration(duration)

    final = CompositeVideoClip([video_clip, overlay, txt_layer])
    final.write_videofile(
        "final_reel.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast"
    )
    print("Video rendered successfully.")

def upload_video_to_github_release():
    print("Uploading video asset to GitHub Releases...")
    tag = f"video-{int(time.time())}"
    release_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "tag_name": tag,
        "name": f"Quran Aesthetic {tag}",
        "draft": False,
        "prerelease": False
    }
    rel_res = requests.post(release_url, headers=headers, json=payload).json()
    upload_url_template = rel_res["upload_url"]
    upload_url = upload_url_template.split("{")[0] + "?name=final_reel.mp4"

    with open("final_reel.mp4", "rb") as f:
        file_data = f.read()

    upload_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "video/mp4"
    }
    asset_res = requests.post(upload_url, headers=upload_headers, data=file_data).json()
    return asset_res["browser_download_url"]

def post_to_tiktok_via_buffer(video_url, surah_name, ayah_num, reciter_name, is_friday):
    print("Sending publish request to Buffer API...")
    clean_surah = surah_name.replace(' ', '_')
    clean_reciter = reciter_name.replace(' ', '_')

    if is_friday:
        caption = (
            f"سورة الكهف نورٌ ما بين الجمعتين 🤍✨\n"
            f"القارئ: {reciter_name}\n\n"
            f"صلّ على النبي ﷺ واكسب أجر نشرها 🌿\n\n"
            f"#سورة_الكهف #يوم_الجمعة #قرآن #تلاوات_خاشعة #{clean_reciter} #quran #fyp"
        )
    else:
        caption = (
            f"سورة {surah_name} 🤍\n"
            f"القارئ: {reciter_name}\n\n"
            f"أرح مسمعك وقلبك بآيات الله 🌿\n\n"
            f"#قرآن #تلاوات_خاشعة #راحة_نفسية #سورة_{clean_surah} #{clean_reciter} #quran #fyp #explore"
        )

    url = "https://api.buffer.com/graphql"
    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    query = """
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

    variables = {
        "input": {
            "channelId": BUFFER_CHANNEL_ID,
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
    }

    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    print("Buffer Response Status:", response.status_code)
    print("Buffer Response Body:", response.text)

if __name__ == "__main__":
    try:
        v_text, s_name, a_num, r_name, is_fri = get_ayah_data()
        download_aesthetic_background()
        build_aesthetic_quran_video(v_text)
        public_url = upload_video_to_github_release()
        print("Uploaded GitHub CDN URL:", public_url)
        post_to_tiktok_via_buffer(public_url, s_name, a_num, r_name, is_fri)
        print("Pipeline finished successfully!")
    except Exception as e:
        print("CRITICAL ERROR ENCOUNTERED:", e)
        sys.exit(1)

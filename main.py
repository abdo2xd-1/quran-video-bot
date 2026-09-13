import os
import time
import random
import requests
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    ColorClip
)

# جلب المفاتيح الأساسية
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

PEXELS_QUERIES = [
    "cinematic rain vertical",
    "calm ocean waves vertical",
    "clouds timelapse vertical",
    "dark forest moody vertical",
    "starry night sky vertical"
]

def get_random_verse_and_audio():
    reciter = random.choice(RECITERS)
    verse_number = random.randint(1, 6236)
    
    url = f"https://api.alquran.cloud/v1/ayah/{verse_number}"
    res = requests.get(url).json()
    data = res["data"]
    
    verse_text = data["text"]
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
        fallback_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{verse_number}.mp3"
        fallback_res = requests.get(fallback_url, headers=headers)
        with open("audio.mp3", "wb") as f:
            f.write(fallback_res.content)
        reciter["name"] = "مشاري العفاسي"
        
    return verse_text, surah_name, int(ayah_num), reciter["name"]

def download_dynamic_background():
    headers = {"Authorization": PEXELS_API_KEY}
    query = random.choice(PEXELS_QUERIES)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=15"
    
    res = requests.get(url, headers=headers).json()
    video_item = random.choice(res["videos"])
    
    video_file = next(f for f in video_item["video_files"] if f.get("width") and f["width"] <= 1080)
    video_url = video_file["link"]
    
    with open("bg.mp4", "wb") as f:
        f.write(requests.get(video_url).content)

def build_quran_video(verse_text, surah_name, ayah_num, reciter_name):
    audio_clip = AudioFileClip("audio.mp3")
    duration = audio_clip.duration + 1.2

    video_clip = VideoFileClip("bg.mp4").subclip(0, duration).resize((1080, 1920))
    video_clip = video_clip.set_audio(audio_clip)

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.40).set_duration(duration)

    font_path = "uthmanic_hafs.ttf" if os.path.exists("uthmanic_hafs.ttf") else "Arial"
    txt_clip = TextClip(
        verse_text,
        fontsize=52,
        color='white',
        font=font_path,
        method='caption',
        size=(900, None),
        align='center'
    ).set_duration(duration).set_position(('center', 'center'))

    meta_text = f"سورة {surah_name} ({ayah_num})\nبصوت الشيخ {reciter_name}"
    meta_clip = TextClip(
        meta_text,
        fontsize=32,
        color='#D4AF37',
        font='Arial',
        align='center'
    ).set_duration(duration).set_position(('center', 220))

    final = CompositeVideoClip([video_clip, overlay, meta_clip, txt_clip])
    final.write_videofile(
        "final_reel.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast"
    )

def upload_video_to_github_release():
    # رفع الفيديو مباشرة إلى سيرفرات GitHub لإنشاء رابط CDN مباشر لا يُحظر أبداً
    tag = f"video-{int(time.time())}"
    release_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. إنشاء Release جديد
    payload = {
        "tag_name": tag,
        "name": f"Quran Video {tag}",
        "draft": False,
        "prerelease": False
    }
    rel_res = requests.post(release_url, headers=headers, json=payload).json()
    upload_url_template = rel_res["upload_url"]
    upload_url = upload_url_template.split("{")[0] + "?name=final_reel.mp4"

    # 2. رفع ملف الفيديو
    with open("final_reel.mp4", "rb") as f:
        file_data = f.read()

    upload_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "video/mp4"
    }
    asset_res = requests.post(upload_url, headers=upload_headers, data=file_data).json()
    direct_download_url = asset_res["browser_download_url"]
    return direct_download_url

def post_to_tiktok_via_buffer(video_url, surah_name, ayah_num, reciter_name):
    caption = (
        f"تلاوة خاشعة لآيات من سورة {surah_name} 🤍\n"
        f"القارئ: {reciter_name} | آية رقم: {ayah_num}\n\n"
        f"صلّ على النبي ﷺ واكتب شيئاً تؤجر عليه في التعليقات 🌿\n"
        f"أعد نشرها لتشارك الأجر والدال على الخير كفاعله 🤲\n\n"
        f"#قرآن #تلاوات_خاشعة #سورة_{surah_name.replace(' ', '_')} #{reciter_name.replace(' ', '_')} #fyp #explore #quran"
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
    v_text, s_name, a_num, r_name = get_random_verse_and_audio()
    download_dynamic_background()
    build_quran_video(v_text, s_name, a_num, r_name)
    public_url = upload_video_to_github_release()
    print("Uploaded GitHub CDN URL:", public_url)
    post_to_tiktok_via_buffer(public_url, s_name, a_num, r_name)

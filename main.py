import os
import sys
import json
import random
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

def get_custom_ayahs_data(surah_num, start_ayah, end_ayah, reciter_id="ar.alafasy", reciter_name="العفاسي"):
    print(f"جاري جلب الآيات للسورة {surah_num} من {start_ayah} إلى {end_ayah}...", flush=True)
    
    # جلب أسماء السور وبياناتها
    meta_url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
    meta_res = requests.get(meta_url).json()
    surah_name = meta_res["data"]["name"]

    verses_text = []
    audio_urls = []

    # جلب الآيات المطلوبة بالصوت والنص
    for a_num in range(start_ayah, end_ayah + 1):
        ayah_url = f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a_num}/{reciter_id}"
        a_res = requests.get(ayah_url).json()
        if a_res.get("status") == "OK":
            verses_text.append(a_res["data"]["text"])
            audio_urls.append(a_res["data"]["audio"])

    # دمج الصوتيات
    combined_audio_path = "recitation.mp3"
    with open(combined_audio_path, "wb") as f_out:
        for url in audio_urls:
            r = requests.get(url)
            f_out.write(r.content)

    full_text = " ۝ ".join(verses_text) + " ۝"
    ayah_range = f"{start_ayah}-{end_ayah}"
    is_friday = (surah_num == 18)

    return full_text, surah_name, ayah_range, reciter_name, is_friday

def download_aesthetic_background():
    print("جاري اختيار وتنزيل خلفية سينمائية من Pexels...", flush=True)
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
            v_data = requests.get(best_link).content
            with open("bg_video.mp4", "wb") as f:
                f.write(v_data)
            return "bg_video.mp4"
    except Exception as e:
        print(f"Pexels fetch warning: {e}", flush=True)

    # خلفية بديلة افتراضية إذا تعذر Pexels
    return "bg_video.mp4"

def build_aesthetic_quran_video(quran_text):
    print("جاري معالجة ومونتاج الفيديو بدقة 1080x1920...", flush=True)
    audio_clip = AudioFileClip("recitation.mp3")
    audio_duration = audio_clip.duration + 1.5

    video_clip = VideoFileClip("bg_video.mp4")
    if video_clip.duration < audio_duration:
        video_clip = video_clip.loop(duration=audio_duration)
    else:
        video_clip = video_clip.subclip(0, audio_duration)

    video_clip = video_clip.resize((1080, 1920))

    # نص الآيات القرآني المنسق
    font_name = "Amiri-Regular" if os.path.exists("/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf") else "Arial"
    
    txt_clip = TextClip(
        quran_text,
        fontsize=48,
        color="white",
        font=font_name,
        method="caption",
        size=(880, None),
        align="center"
    ).set_duration(audio_duration).set_position(("center", "center"))

    final = CompositeVideoClip([video_clip, txt_clip]).set_audio(audio_clip)
    final.write_videofile(
        "final_reel.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast"
    )
    print("تم إخراج الفيديو بنجاح: final_reel.mp4", flush=True)
    return "final_reel.mp4"

def upload_video_to_github_release():
    print("جاري رفع الفيديو إلى GitHub Releases...", flush=True)
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    tag_name = f"video-{int(random.random()*1000000000)}"

    # إنشاء Release جديد
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
    res = requests.post(create_url, headers=headers, json=rel_data).json()
    upload_url = res["upload_url"].split("{")[0]

    # رفع ملف الفيديو المكتمل
    with open("final_reel.mp4", "rb") as f:
        up_headers = {
            "Authorization": f"token {gh_token}",
            "Content-Type": "video/mp4"
        }
        up_res = requests.post(
            f"{upload_url}?name=final_reel.mp4",
            headers=up_headers,
            data=f
        ).json()

    public_download_url = up_res.get("browser_download_url")
    print(f"الرابط المباشر للتحميل: {public_download_url}", flush=True)
    return public_download_url

def post_to_tiktok_via_buffer(video_url, surah_name, ayah_range, reciter_name, is_friday=False):
    """
    نشر الفيديو دفعة واحدة على جميع الحسابات المربوطة في Buffer (TikTok, YouTube Shorts, Instagram Reels)
    """
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()

    if not buffer_token or not channels_raw:
        print("Buffer access token or Channel IDs not found. Skipping Buffer.", flush=True)
        return

    # استخراج كل الـ IDs الممررة
    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]

    caption = (
        f"سورة {surah_name} 🤍 (الآيات {ayah_range})\n"
        f"القارئ: {reciter_name}\n\n"
        f"أرح مسمعك وقلبك بآيات الله 🌿\n\n"
        f"#قرآن #تلاوات_خاشعة #راحة_نفسية #سورة_{surah_name.replace(' ', '_')} "
        f"#{reciter_name.replace(' ', '_')} #quran #fyp #explore #reels #shorts"
    )

    headers = {
        "Authorization": f"Bearer {buffer_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    print(f"جاري إرسال المنشور إلى {len(channel_ids)} قناة عبر Buffer...", flush=True)

    for ch_id in channel_ids:
        payload = {
            "profile_ids[]": ch_id,
            "text": caption,
            "media[video]": video_url,
            "now": "true"
        }

        try:
            res = requests.post(
                "https://api.bufferapp.com/1/updates/create.json",
                headers=headers,
                data=payload,
                timeout=30
            )
            data = res.json()
            if data.get("success"):
                print(f"✅ تم الإرسال بنجاح إلى القناة: {ch_id}", flush=True)
            else:
                print(f"⚠️ تنبيه للقناة {ch_id}: {data.get('message')}", flush=True)
        except Exception as e:
            print(f"❌ خطأ أثناء الإرسال إلى {ch_id}: {e}", flush=True)

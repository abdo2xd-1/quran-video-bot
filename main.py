import os
import sys
import json
import time
import uuid
import base64
import random
import shutil
import datetime
import subprocess
import requests

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None).LANCZOS if hasattr(PIL.Image, 'Resampling') else None)

from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)

HISTORY_FILE = "history_shorts_all.json"
QURAN_FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf"

# الرابط المباشر لمشهد الشارع المبلل والترام تحت المطر بفرنسا
EXACT_BORDEAUX_RAIN_VIDEO = "https://assets.mixkit.co/videos/preview/mixkit-walking-down-a-wet-street-with-tram-tracks-in-bordeaux-41315-large.mp4"

RECITERS_POOL = [
    {"name": "محمد صديق المنشاوي", "server": "https://server10.mp3quran.net/minsh"},
    {"name": "ياسر الدوسري", "server": "https://server11.mp3quran.net/yasser"}
]

SEO_TAGS_YOUTUBE = "القرآن الكريم, تلاوة خاشعة, راحة نفسية, سورة, عبدالرحمن مسعد, يوم الجمعة, سورة الكهف, تلاوات قصيرة, quran, shorts, islam, quran recitation"
SEO_HASHTAGS = "#القرآن_الكريم #تلاوة_خاشعة #راحة_نفسية #قرآن #shorts #reels #islam"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"posted_keys": [], "kahf_progress": {"week": None, "next_ayah": 1, "part": 1}, "used_bg_ids": []}
    return {"posted_keys": [], "kahf_progress": {"week": None, "next_ayah": 1, "part": 1}, "used_bg_ids": []}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_font_base64():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path) or os.path.getsize(font_path) < 40000:
        try:
            r = requests.get(QURAN_FONT_URL, timeout=25)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except Exception:
            pass
    if os.path.exists(font_path):
        with open(font_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    return ""

def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']:
        text = text.replace(s, '')
    return text.strip()

def to_arabic_num(num):
    arabic_digits = {'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'}
    return "".join(arabic_digits.get(c, c) for c in str(num))

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

def download_surah_segment(surah_num, start_a, end_a, reciter_info, out_file):
    s_str = f"{surah_num:03d}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    surah_full_url = f"{reciter_info['server']}/{s_str}.mp3"
    raw_surah = f"raw_surah_{s_str}.mp3"

    print("📥 جلب تلاوة السورة بنقائها الأصلي...", flush=True)
    res = requests.get(surah_full_url, headers=headers, timeout=60, stream=True)
    if res.status_code != 200:
        surah_full_url = f"https://server8.mp3quran.net/afs/{s_str}.mp3"
        res = requests.get(surah_full_url, headers=headers, timeout=60, stream=True)

    with open(raw_surah, "wb") as f:
        for chunk in res.iter_content(chunk_size=16384):
            f.write(chunk)

    try:
        t_url = f"https://api.quran.com/api/v4/recitations/7/by_ayah?surah_number={surah_num}"
        timing_data = requests.get(t_url, headers=headers, timeout=15).json()
        audio_files = timing_data.get("audio_files", [])
        
        start_ms = 0
        end_ms = None
        for item in audio_files:
            verse_key = item.get("verse_key", "")
            if verse_key == f"{surah_num}:{start_a}":
                start_ms = item.get("segments", [[0, 0]])[0][2] if item.get("segments") else 0
            if verse_key == f"{surah_num}:{end_a}":
                segments = item.get("segments", [])
                end_ms = segments[-1][3] if segments else None

        start_sec = max(0, start_ms / 1000.0)
        dur_sec = max(5.0, (end_ms / 1000.0) - start_sec) if end_ms else 45.0
    except Exception:
        start_sec = 0
        dur_sec = 45.0

    raw_segment = f"raw_segment_{s_str}.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start_sec), "-t", str(dur_sec), "-i", raw_surah,
        "-c", "copy", raw_segment
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([
        "ffmpeg", "-y", "-i", raw_segment, "-c:a", "copy", out_file
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(raw_surah): os.remove(raw_surah)
    if os.path.exists(raw_segment): os.remove(raw_segment)
    return True

# تم تحديث هذه الدالة بالكامل لمعالجة الخطأ 183
def prepare_exact_bordeaux_video(tag, min_duration):
    raw_bg = f"raw_bordeaux_{tag}.mp4"
    fast_bg = f"ready_bordeaux_{tag}.mp4"

    print("🎥 جلب فيديو المطر ومسار الترام الأصلي...", flush=True)
    # إضافة User-Agent حقيقي لمنع السيرفر من رفض التحميل
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(EXACT_BORDEAUX_RAIN_VIDEO, headers=headers, timeout=60)
        res.raise_for_status()
        with open(raw_bg, "wb") as f:
            f.write(res.content)
    except Exception as e:
        print(f"⚠️ خطأ في تحميل فيديو Mixkit، جاري استخدام فيديو بديل: {e}", flush=True)
        # فيديو مطر سينمائي بديل من Pexels يعمل كملاذ آمن
        fallback_url = "https://videos.pexels.com/video-files/2491294/2491294-hd_1080_1920_30fps.mp4"
        res = requests.get(fallback_url, headers=headers, timeout=60)
        with open(raw_bg, "wb") as f:
            f.write(res.content)

    scale_cmd = [
        "ffmpeg", "-y", "-i", raw_bg,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-b:v", "6000k", "-an", fast_bg
    ]
    subprocess.run(scale_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(raw_bg): 
        os.remove(raw_bg)
    return fast_bg

def render_lower_verse_frame(verse_text, timer_str, idx, font_b64):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ 
    width: 1080px; 
    height: 1920px; 
    background: transparent; 
    display: flex; 
    flex-direction: column;
    justify-content: flex-end; 
    align-items: center; 
    position: relative; 
    font-family: 'Amiri', serif;
    padding-bottom: 310px;
  }}
  .verse-box {{ 
    direction: rtl; 
    text-align: center; 
    color: #FFFFFF; 
    font-size: 56px; 
    font-weight: normal; 
    line-height: 1.8;
    max-width: 900px;
    padding: 0 40px;
    text-shadow: 
      0 2px 10px rgba(0, 0, 0, 0.95),
      0 4px 25px rgba(0, 0, 0, 0.85);
  }}
  .timer {{ 
    margin-top: 15px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    font-size: 26px; 
    color: rgba(255, 255, 255, 0.7); 
    letter-spacing: 1px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.9);
    direction: ltr;
  }}
</style></head>
<body>
  <div class="verse-box">{verse_text}</div>
  <div class="timer">{timer_str}</div>
</body></html>"""

    h_path, p_path = f"tmp_{idx}.html", f"frame_{idx}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([
        chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", 
        "--window-size=1080,1920", "--default-background-color=00000000", 
        f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): 
        os.remove(h_path)
    return p_path

def generate_emerald_blue_card(bg_video_path, surah_name, sub_title, reciter_name, font_b64, out_cover):
    chrome_bin = get_chrome()
    frame_bg = "thumb_bg.jpg"
    
    subprocess.run([
        "ffmpeg", "-y", "-ss", "3.0", "-i", bg_video_path, "-vframes", "1", "-q:v", "1", frame_bg
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    bg_data_uri = ""
    if os.path.exists(frame_bg):
        with open(frame_bg, "rb") as f:
            bg_data_uri = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('ascii')}"

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); font-weight: bold; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ 
    width: 1080px; 
    height: 1920px; 
    background: url('{bg_data_uri}') center center / cover no-repeat;
    display: flex; 
    justify-content: center; 
    align-items: center; 
    position: relative; 
    font-family: 'Amiri', serif;
    overflow: hidden;
  }}
  .backdrop-overlay {{
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at center, rgba(8, 24, 38, 0.5) 0%, rgba(5, 15, 12, 0.85) 100%),
                linear-gradient(180deg, rgba(13, 27, 42, 0.45) 0%, rgba(9, 21, 16, 0.6) 100%);
    backdrop-filter: blur(14px) brightness(0.62);
  }}
  .particle-glow {{
    position: absolute;
    width: 100%;
    height: 100%;
    background-image: 
      radial-gradient(circle at 20% 30%, rgba(0, 150, 255, 0.1) 0%, transparent 40%),
      radial-gradient(circle at 80% 70%, rgba(16, 185, 129, 0.1) 0%, transparent 40%);
  }}
  .glass-card {{
    position: relative;
    z-index: 2;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(32px) saturate(180%);
    -webkit-backdrop-filter: blur(32px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 40px;
    padding: 70px 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    box-shadow: 0 40px 80px rgba(0, 0, 0, 0.7), 
                inset 0 1px 1px rgba(255, 255, 255, 0.2);
    max-width: 880px;
    width: 88%;
  }}
  .badge {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.85);
    margin-bottom: 30px;
    background: rgba(255, 255, 255, 0.12);
    padding: 8px 32px;
    border-radius: 30px;
    border: 1px solid rgba(255, 255, 255, 0.18);
  }}
  .title {{
    font-size: 100px;
    font-weight: bold;
    color: #FFFFFF;
    margin-bottom: 20px;
    text-shadow: 0 4px 30px rgba(255, 255, 255, 0.22), 
                0 0 35px rgba(0, 150, 255, 0.35),
                0 2px 12px rgba(0, 0, 0, 0.8);
  }}
  .sub {{
    font-size: 46px;
    color: #E2E8F0;
    margin-bottom: 25px;
    text-shadow: 0 2px 12px rgba(0, 0, 0, 0.75);
  }}
  .reciter {{
    font-size: 34px;
    color: rgba(255, 255, 255, 0.65);
    letter-spacing: 0.5px;
  }}
</style></head>
<body>
  <div class="backdrop-overlay"></div>
  <div class="particle-glow"></div>
  <div class="glass-card">
    <div class="badge">Holy Quran • تلاوة خاشعة</div>
    <div class="title">سورة {surah_name}</div>
    <div class="sub">{sub_title}</div>
    <div class="reciter">القارئ {reciter_name}</div>
  </div>
</body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([
        chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", 
        "--window-size=1080,1920", f"--screenshot={os.path.abspath(out_cover)}", 
        f"file://{os.path.abspath(h_path)}"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(h_path): os.remove(h_path)
    if os.path.exists(frame_bg): os.remove(frame_bg)
    return out_cover

def build_fast_short_video(surah_num, surah_name, start_a, end_a, badge_label, reciter_info, tag, history):
    font_b64 = get_font_base64()
    rec_name = reciter_info["name"]

    aud_file = f"aud_seg_{tag}.mp3"
    download_surah_segment(surah_num, start_a, end_a, reciter_info, aud_file)
    audio_clip = AudioFileClip(aud_file)

    if audio_clip.duration > 48.0:
        audio_clip = audio_clip.subclip(0, 48.0)

    verses_payload = []
    for a in range(start_a, end_a + 1):
        try:
            t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=10).json()
            txt = clean_arabic(t_res.get("data", {}).get("text", ""))
            if a == 1 and surah_num != 1:
                txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()
            num_symbol = f" ﴿{to_arabic_num(a)}﴾"
            verses_payload.append(txt + num_symbol)
        except Exception:
            continue

    tot_dur = audio_clip.duration
    v_count = len(verses_payload) if verses_payload else 1
    per_verse_dur = tot_dur / v_count

    text_clips = []
    for idx, verse_str in enumerate(verses_payload):
        start_t = idx * per_verse_dur
        dur_t = per_verse_dur
        mins = int(start_t // 60)
        secs = int(start_t % 60)
        timer_str = f"{mins:02d}:{secs:02d}"

        frame_img = render_lower_verse_frame(verse_str, timer_str, idx, font_b64)
        text_clips.append(ImageClip(frame_img).set_start(start_t).set_duration(dur_t).set_position(("center", "bottom")))

    fast_bg = prepare_exact_bordeaux_video(tag, tot_dur)
    bg = VideoFileClip(fast_bg)
    bg = bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)
    
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.18).set_duration(tot_dur)
    main_video = CompositeVideoClip([bg, dim] + text_clips).set_audio(audio_clip).set_duration(tot_dur)

    cover_file = f"cover_{tag}.jpg"
    generate_emerald_blue_card(fast_bg, surah_name, f"الآيات ({start_a}-{end_a})", rec_name, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.10)

    temp_joined = f"temp_{tag}.mp4"
    joined = concatenate_videoclips([cover_clip, main_video])
    
    joined.write_videofile(
        temp_joined, fps=30, codec="libx264", audio_codec="aac", 
        bitrate="6000k", threads=4, preset="medium"
    )

    out_file = f"final_{tag}.mp4"
    embed_cmd = [
        "ffmpeg", "-y", "-i", temp_joined, "-i", cover_file, 
        "-map", "0", "-map", "1", "-c", "copy", 
        "-map_metadata", "-1",
        "-disposition:v:1", "attached_pic", out_file
    ]
    try:
        subprocess.run(embed_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        out_file = temp_joined

    if os.path.exists(aud_file): os.remove(aud_file)
    if os.path.exists(fast_bg): os.remove(fast_bg)
    if os.path.exists(temp_joined) and temp_joined != out_file: os.remove(temp_joined)

    return out_file, cover_file, rec_name

def upload_files(video_file):
    print("📤 رفع ملف Shorts للحصول على رابط مباشر لـ Buffer...", flush=True)
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if repo and gh_token:
        tag_name = f"v-short-{int(time.time()*1000)}"
        try:
            res = requests.post(
                f"https://api.github.com/repos/{repo}/releases",
                headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
                json={"tag_name": tag_name, "name": f"Short {tag_name}", "draft": False}, timeout=30
            ).json()
            if "upload_url" in res:
                u_url = res["upload_url"].split("{")[0]
                with open(video_file, "rb") as vf:
                    up_res = requests.post(f"{u_url}?name=video.mp4", headers={"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}, data=vf, timeout=120).json()
                browser_url = up_res.get("browser_download_url")
                if browser_url:
                    print(f"✅ تم الرفع كـ Release على GitHub: {browser_url}", flush=True)
                    return browser_url
        except Exception as e:
            print(f"⚠️ خطأ في GitHub Releases: {e}", flush=True)

    try:
        with open(video_file, "rb") as f:
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=120)
            if r.status_code == 200 and r.text.startswith("http"):
                url = r.text.strip()
                print(f"✅ تم الرفع على Catbox بنجاح: {url}", flush=True)
                return url
    except Exception as e:
        print(f"⚠️ خطأ في Catbox: {e}", flush=True)

    return None

def post_to_buffer(video_url, yt_title, caption):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()
    if not buffer_token or not channels_raw:
        print("⚠️ بيانات Buffer غير مكتملة، تم التخطي.", flush=True)
        return
    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
    graphql_url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {buffer_token}", "Content-Type": "application/json"}
    mutation = """mutation CreatePost($input: CreatePostInput!) { 
        createPost(input: $input) { 
            ... on PostActionSuccess { post { id status } } 
            ... on MutationError { message } 
        } 
    }"""

    for ch_id in channel_ids:
        post_input = {
            "channelId": ch_id, 
            "text": caption, 
            "mode": "shareNow", 
            "schedulingType": "automatic",
            "assets": [{"video": {"url": video_url}}]
        }

        if ch_id in ["6aa9df26ea19ca0bde51b3c5", "6aa72b30ea19ca0bde39598b"]:
            post_input["metadata"] = {"youtube": {"title": yt_title[:95], "categoryId": "27"}}
        elif ch_id == "6aa6d1fbea19ca0bde35e91c":
            post_input["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}

        try:
            res = requests.post(graphql_url, headers=headers, json={"query": mutation, "variables": {"input": post_input}}, timeout=35).json()
            post_data = res.get("data", {}).get("createPost", {})
            if "post" in post_data:
                print(f"✅ نجح إرسال Shorts لـ Buffer للقناة {ch_id} (Post ID: {post_data['post'].get('id')})", flush=True)
            else:
                print(f"❌ رد Buffer للقناة {ch_id}: {post_data.get('message', res)}", flush=True)
        except Exception as e:
            print(f"❌ خطأ أثناء الاتصال بـ Buffer: {e}", flush=True)

def post_to_dailymotion(video_file, title, description, tags="quran,islam,shorts"):
    api_key = os.getenv("DAILYMOTION_KEY", "").strip()
    api_secret = os.getenv("DAILYMOTION_SECRET", "").strip()
    username = os.getenv("DAILYMOTION_USERNAME", "").strip()
    password = os.getenv("DAILYMOTION_PASSWORD", "").strip()

    if not all([api_key, api_secret, username, password]):
        print("⚠️ بيانات Dailymotion غير مكتملة، تم التخطي.", flush=True)
        return None

    try:
        print("🚀 جاري تسجيل الدخول ورفع الفيديو على Dailymotion...", flush=True)
        token_res = requests.post(
            "https://api.dailymotion.com/oauth/token",
            data={
                "grant_type": "password",
                "client_id": api_key,
                "client_secret": api_secret,
                "username": username,
                "password": password,
                "scope": "manage_videos"
            },
            timeout=30
        ).json()

        access_token = token_res.get("access_token")
        if not access_token:
            print(f"❌ فشل تسجيل الدخول إلى Dailymotion: {token_res}", flush=True)
            return None

        headers = {"Authorization": f"Bearer {access_token}"}

        upload_url_res = requests.get(
            "https://api.dailymotion.com/file/upload",
            headers=headers,
            timeout=20
        ).json()
        upload_url = upload_url_res.get("upload_url")

        with open(video_file, "rb") as f:
            up_res = requests.post(upload_url, files={"file": f}, timeout=180).json()
        file_url = up_res.get("url")

        if not file_url:
            print("❌ فشل نقل ملف الفيديو لسيرفر Dailymotion.", flush=True)
            return None

        publish_data = {
            "url": file_url,
            "title": title[:250],
            "description": description,
            "tags": tags,
            "channel": "lifestyle",
            "published": "true",
            "is_created_for_kids": "false"
        }
        create_res = requests.post(
            "https://api.dailymotion.com/me/videos",
            headers=headers,
            data=publish_data,
            timeout=30
        ).json()

        video_id = create_res.get("id")
        if video_id:
            dm_link = f"https://www.dailymotion.com/video/{video_id}"
            print(f"✅ تم نشر الفيديو بنجاح على Dailymotion: {dm_link}", flush=True)
            return dm_link
        else:
            err_data = create_res.get("error", {})
            if err_data.get("code") == 403:
                print("⏳ تم الوصول للحد الأقصى لعدد رفوعات Dailymotion اليوم، سيتجدد غداً تلقائياً.", flush=True)
            else:
                print(f"❌ فشل نشر الفيديو في Dailymotion: {create_res}", flush=True)

    except Exception as e:
        print(f"⚠️ خطأ أثناء النشر على Dailymotion: {e}", flush=True)

    return None

def post_to_odysee(video_file, title, description, tags=None):
    if tags is None:
        tags = ["quran", "islam", "shorts", "reels"]

    auth_token = os.getenv("ODYSEE_AUTH_TOKEN", "").strip()
    if not auth_token or not os.path.exists(video_file):
        print("⚠️ بيانات Odysee أو ملف الفيديو غير موجود، تم التخطي.", flush=True)
        return None

    try:
        headers = {
            "Content-Type": "application/json-rpc",
            "X-Lbry-Auth-Token": auth_token
        }

        channel_id = "d2a1e5238cbfc0b0a210a7f7d1d815c5f075d9a4"
        file_size = os.path.getsize(video_file)
        file_name = os.path.basename(video_file)
        clean_stream_name = f"quran-short-{int(time.time())}"

        meta_fn = base64.b64encode(file_name.encode()).decode()
        meta_tk = base64.b64encode(auth_token.encode()).decode()

        upload_servers = [
            "https://upload.lbry.com/upload",
            "https://api.odysee.com/upload"
        ]

        upload_location = None
        for srv in upload_servers:
            try:
                init_res = requests.post(
                    srv,
                    headers={
                        "Tus-Resumable": "1.0.0",
                        "Upload-Length": str(file_size),
                        "Upload-Metadata": f"filename {meta_fn},auth_token {meta_tk}"
                    },
                    timeout=15
                )
                loc = init_res.headers.get("Location")
                if loc:
                    if loc.startswith("/"):
                        from urllib.parse import urlparse
                        p = urlparse(srv)
                        loc = f"{p.scheme}://{p.netloc}{loc}"
                    upload_location = loc
                    break
            except Exception:
                continue

        if not upload_location:
            print("ℹ️ تم تخطي رفع Odysee المباشر مؤقتاً لعدم استجابة خوادم TUS.", flush=True)
            return None

        with open(video_file, "rb") as vf:
            patch_res = requests.patch(
                upload_location,
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Offset": "0",
                    "Content-Type": "application/offset+octet-stream"
                },
                data=vf,
                timeout=300
            )

        if patch_res.status_code not in [200, 204]:
            return None

        file_id = upload_location.rstrip("/").split("/")[-1]

        publish_params = {
            "name": clean_stream_name,
            "title": title[:95],
            "description": description,
            "tags": tags,
            "languages": ["ar"],
            "bid": "0.0001",
            "file_path": file_id,
            "channel_id": channel_id
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "publish",
            "params": publish_params,
            "id": int(time.time())
        }

        pub_res = requests.post(
            "https://api.na-backend.odysee.com/api/v1/proxy?m=publish",
            headers=headers,
            json=payload,
            timeout=60
        ).json()

        claim_info = pub_res.get("result", {}).get("outputs", [{}])[0]
        claim_name = claim_info.get("name")
        res_claim_id = claim_info.get("claim_id")

        if claim_name and res_claim_id:
            odysee_url = f"https://odysee.com/{claim_name}:{res_claim_id}"
            print(f"✅ تم النشر بنجاح على Odysee: {odysee_url}", flush=True)
            return odysee_url
    except Exception as e:
        print(f"⚠️ استثناء في Odysee: {e}", flush=True)

    return None

def notify_telegram(message, cover_file=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        if cover_file and os.path.exists(cover_file):
            with open(cover_file, "rb") as pf:
                requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", data={"chat_id": chat_id, "caption": "📸 الغلاف المعتمد 🌿"}, files={"photo": pf}, timeout=20)
    except Exception:
        pass

def get_friday_kahf_chunk(history, current_week_str):
    k_prog = history.get("kahf_progress", {})
    if k_prog.get("week") != current_week_str:
        start_a = 1
        part_num = 1
    else:
        start_a = k_prog.get("next_ayah", 1)
        part_num = k_prog.get("part", 1)

    if start_a > 110:
        start_a = 1
        part_num = 1

    chunk_size = 4
    end_a = min(110, start_a + chunk_size - 1)
    clip_key = f"kahf_{current_week_str}_p{part_num}_{start_a}_{end_a}"

    history["kahf_progress"] = {
        "week": current_week_str,
        "next_ayah": end_a + 1,
        "part": part_num + 1
    }

    return {
        "surah": 18,
        "name": "الكهف",
        "start": start_a,
        "end": end_a,
        "part": part_num,
        "key": clip_key,
        "badge": f"سورة الكهف (جزء {part_num}) 🌿"
    }

def pick_unposted_clip_all_quran(history):
    surahs_meta_file = "surahs_114_meta.json"
    if os.path.exists(surahs_meta_file):
        with open(surahs_meta_file, "r", encoding="utf-8") as f:
            surahs = json.load(f)
    else:
        try:
            r = requests.get("https://api.alquran.cloud/v1/meta", timeout=20).json()
            raw_s = r.get("data", {}).get("surahs", {}).get("references", [])
            surahs = [{"number": s["number"], "name": s["name"].replace("سُورَةُ ", "").strip(), "ayahs": s["numberOfAyahs"]} for s in raw_s]
            with open(surahs_meta_file, "w", encoding="utf-8") as f:
                json.dump(surahs, f, ensure_ascii=False)
        except Exception:
            surahs = [{"number": 1, "name": "الفاتحة", "ayahs": 7}, {"number": 18, "name": "الكهف", "ayahs": 110}, {"number": 67, "name": "الملك", "ayahs": 30}]

    posted_keys = set(history.get("posted_keys", []))
    for _ in range(300):
        surah = random.choice(surahs)
        if surah["number"] == 18:
            continue
        s_num = surah["number"]
        s_name = surah["name"]
        total_ayahs = surah["ayahs"]
        chunk_size = 3 if total_ayahs >= 3 else total_ayahs
        start_a = random.randint(1, max(1, total_ayahs - chunk_size + 1))
        end_a = min(total_ayahs, start_a + chunk_size - 1)
        clip_key = f"{s_num}_{start_a}_{end_a}"
        if clip_key not in posted_keys:
            return {
                "surah": s_num,
                "name": s_name,
                "start": start_a,
                "end": end_a,
                "part": None,
                "key": clip_key,
                "badge": f"سورة {s_name} 🌿"
            }

    history["posted_keys"] = []
    s = random.choice([x for x in surahs if x["ayahs"] >= 3 and x["number"] != 18])
    return {"surah": s["number"], "name": s["name"], "start": 1, "end": 3, "part": None, "key": f"{s['number']}_1_3_{int(time.time())}", "badge": f"سورة {s['name']} 🌿"}

if __name__ == "__main__":
    local_egypt_time = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    is_friday = (local_egypt_time.weekday() == 4)
    reciter = random.choice(RECITERS_POOL)
    history = load_history()

    if is_friday:
        week_str = local_egypt_time.strftime("%Y_%U")
        item = get_friday_kahf_chunk(history, week_str)
        print(f"🌟 يوم الجمعة المبارك بتوقيت مصر: إنتاج سورة الكهف (جزء {item['part']}) - الآيات ({item['start']}-{item['end']})...", flush=True)
        yt_title = f"سورة الكهف كاملة | الجزء {item['part']} الآيات ({item['start']}-{item['end']}) 🌿 راحة نفسية القارئ {reciter['name']} #shorts"
        caption = (
            f"📖 سورة الكهف - الجزء {item['part']}\n"
            f"✨ الآيات الكريمة: ({item['start']} - {item['end']})\n"
            f"🎙️ بصوت القارئ: {reciter['name']}\n\n"
            f"تلاوة خاشعة تريح القلوب من سورة الكهف المباركة ليوم الجمعة 🤍\n"
            f"قال ﷺ: (من قرأ سورة الكهف في يوم الجمعة أضاء له من النور ما بين الجمعتين)\n\n"
            f"لا تنسى الاشتراك وتفعيل الجرس ليصلك كل جديد 🎧\n\n"
            f"{SEO_HASHTAGS} #يوم_الجمعة #سورة_الكهف"
        )
    else:
        item = pick_unposted_clip_all_quran(history)
        print(f"🎬 اختيار مقطع Shorts من القرآن: سورة {item['name']} الآيات ({item['start']}-{item['end']})...", flush=True)
        yt_title = f"تلاوة خاشعة تريح القلوب | سورة {item['name']} الآيات ({item['start']}-{item['end']}) 🤍 القارئ {reciter['name']} #shorts"
        caption = (
            f"📖 سورة {item['name']} | الآيات ({item['start']} - {item['end']})\n"
            f"🎙️ بصوت القارئ: {reciter['name']}\n\n"
            f"اللهم اجعل القرآن ربيع قلوبنا ونور صدورنا وجلاء أحزاننا ونوراً لنا في الدنيا والآخرة 🤍\n\n"
            f"اشترك في القناة لدعم نشر كتاب الله والمساهمة في الأجر 🎧\n\n"
            f"{SEO_HASHTAGS} #سورة_{item['name']} #تلاوة_خاشعة"
        )

    tag = f"short_{item['key']}_{int(time.time())}"

    vid_file, cov_file, r_name = build_fast_short_video(
        item["surah"], item["name"], item["start"], item["end"],
        item["badge"], reciter, tag, history
    )

    pub_url = upload_files(vid_file)

    if pub_url:
        post_to_buffer(pub_url, yt_title, caption)
    else:
        print("❌ فشل الحصول على رابط تحميل للفيديو، لم يتم الإرسال لـ Buffer.", flush=True)

    dm_link = post_to_dailymotion(vid_file, yt_title, caption, tags=SEO_TAGS_YOUTUBE)
    odysee_link = post_to_odysee(vid_file, yt_title, caption, tags=SEO_TAGS_YOUTUBE.split(", "))

    if not is_friday:
        if item["key"] not in history["posted_keys"]:
            history["posted_keys"].append(item["key"])

    save_history(history)

    dm_report = f"\n📺 <b>Dailymotion:</b> <a href='{dm_link}'>مشاهدة على ديلي موشن</a>" if dm_link else ""
    odysee_report = f"\n🎥 <b>Odysee:</b> <a href='{odysee_link}'>مشاهدة على أوديسي</a>" if odysee_link else ""
    report = (
        f"✨ <b>تم إنتاج ونشر مقطع قرآن سينمائي جديد بنجاح!</b>\n\n"
        f"📖 <b>السورة:</b> {item['name']} " + (f"(جزء {item['part']})" if item.get("part") else "") + f"\n"
        f"🔢 <b>الآيات:</b> ({item['start']} إلى {item['end']})\n"
        f"🎙️ <b>القارئ:</b> {r_name}\n"
        f"🌧️ <b>النمط:</b> المشهد الأصلي لشوارع بوردو الماطرة مع رسم عثماني دقيق\n"
        f"🔒 <b>كود السجل:</b> <code>{item['key']}</code>\n"
        f"🔗 <b>الرابط المباشر:</b> <a href='{pub_url}'>تحميل المقطع</a>"
        f"{dm_report}"
        f"{odysee_report}"
    )
    notify_telegram(report, cov_file)

    if os.path.exists(vid_file): os.remove(vid_file)
    if os.path.exists(cov_file): os.remove(cov_file)
    print("=== اكتمل الرندر للشورتس، التحديث، والنشر بنجاح ===", flush=True)

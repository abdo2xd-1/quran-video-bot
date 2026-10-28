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
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

RECITERS_POOL = [
    {"name": "مشاري العفاسي", "server": "https://server8.mp3quran.net/afs"},
    {"name": "علي الحذيفي", "server": "https://server9.mp3quran.net/hthfi"},
    {"name": "أبو بكر الشاطري", "server": "https://server11.mp3quran.net/shatri"},
    {"name": "محمد أيوب", "server": "https://server8.mp3quran.net/ayyub"}
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"posted_keys": [], "kahf_progress": {"week": None, "next_ayah": 1, "part": 1}}
    return {"posted_keys": [], "kahf_progress": {"week": None, "next_ayah": 1, "part": 1}}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_all_114_surahs():
    cache_path = "surahs_114_meta.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        r = requests.get("https://api.alquran.cloud/v1/meta", timeout=20).json()
        surahs = r.get("data", {}).get("surahs", {}).get("references", [])
        meta = [{"number": s["number"], "name": s["name"].replace("سُورَةُ ", "").strip(), "ayahs": s["numberOfAyahs"]} for s in surahs]
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        return meta
    except Exception:
        return [{"number": 1, "name": "الفاتحة", "ayahs": 7}, {"number": 18, "name": "الكهف", "ayahs": 110}, {"number": 105, "name": "الفيل", "ayahs": 5}]

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

    end_a = min(110, start_a + 2)
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
        "badge": f"الكهف (جزء {part_num}) 🌿"
    }

def pick_unposted_clip_all_quran(history):
    surahs = get_all_114_surahs()
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

def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ', '\u06dd', '\u06de', '\u06d6', '\u06d7', '\u06d8', '\u06d9', '\u06da', '\u06db', '\u06dc']:
        text = text.replace(s, '')
    return text.strip()

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

def apply_anti_copyright(raw_audio, out_audio):
    cmd = [
        "ffmpeg", "-y",
        "-i", raw_audio,
        "-filter_complex", 
        "[0:a]asetrate=44100*1.035,atempo=0.966,volume=1.15[aout]",
        "-map", "[aout]", "-b:a", "192k", "-ar", "44100", out_audio
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_audio

def download_surah_segment(surah_num, start_a, end_a, reciter_info, out_file):
    s_str = f"{surah_num:03d}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    surah_full_url = f"{reciter_info['server']}/{s_str}.mp3"
    raw_surah = f"raw_surah_{s_str}.mp3"

    print("📥 جلب تلاوة السورة مباشرة من CDN...", flush=True)
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

    apply_anti_copyright(raw_segment, out_file)

    if os.path.exists(raw_surah): os.remove(raw_surah)
    if os.path.exists(raw_segment): os.remove(raw_segment)
    return True

def render_quran_frame(words, active_idx, badge_text, font_b64):
    chrome_bin = get_chrome()
    words_html = []
    for i, w in enumerate(words):
        if i == active_idx:
            words_html.append(f'<span style="color:#D4AF37; transform:scale(1.08); text-shadow:0 0 16px rgba(212,175,55,0.95); display:inline-block;">{w}</span>')
        else:
            words_html.append(f'<span style="color:#FFFFFF; text-shadow:0 0 10px rgba(0,0,0,0.95);">{w}</span>')

    full_verse = " ".join(words_html)
    font_size = 64 if len(words) <= 8 else (48 if len(words) <= 16 else 38)

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
    justify-content: center; 
    align-items: center; 
    position: relative; 
    font-family: 'Amiri';
  }}
  .badge {{ 
    position: absolute; 
    top: 220px; 
    background: rgba(10,14,20,0.75); 
    border: 1px solid rgba(212,175,55,0.5); 
    color: #fff; 
    font-size: 28px; 
    padding: 10px 32px; 
    border-radius: 30px; 
  }}
  .ayah {{ 
    direction: rtl; 
    text-align: center; 
    font-size: {font_size}px; 
    font-weight: bold; 
    line-height: 2.0; 
    max-width: 920px; 
    margin: auto 0; 
  }}
  .watermark {{ 
    position: absolute; 
    bottom: 140px; 
    left: 50%; 
    transform: translateX(-50%); 
    font-size: 24px; 
    color: rgba(255,255,255,0.5); 
    direction: ltr; 
  }}
</style></head>
<body>
  <div class="badge">🎧 {badge_text} 🌿</div>
  <div class="ayah">{full_verse}</div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path, p_path = f"tmp_{active_idx}.html", f"frame_{active_idx}.png"
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

def generate_cover_file(surah_name, sub_title, reciter_name, font_b64, out_cover):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ 
    width: 1080px; 
    height: 1920px; 
    background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    position: relative; 
    font-family: 'Amiri';
  }}
  .box {{ 
    width: 1080px; 
    height: 1080px; 
    display: flex; 
    flex-direction: column; 
    justify-content: center; 
    align-items: center; 
    text-align: center; 
  }}
  .badge {{ 
    font-size: 26px; 
    color: #fff; 
    background: rgba(0,0,0,0.5); 
    padding: 8px 24px; 
    border-radius: 20px; 
    border: 1px solid rgba(212,175,55,0.3); 
    margin-bottom: 20px; 
  }}
  .title {{ 
    font-size: 82px; 
    font-weight: bold; 
    color: #D4AF37; 
    margin-bottom: 15px; 
    text-shadow: 0 0 20px rgba(212,175,55,0.8); 
  }}
  .reciter {{ 
    font-size: 38px; 
    color: #fff; 
    margin-bottom: 15px; 
  }}
  .sub {{ 
    font-size: 26px; 
    color: rgba(212,175,55,0.9); 
  }}
</style></head>
<body><div class="box">
  <div class="badge">🕌 تلاوة خاشعة بالذهب 🌿</div>
  <div class="title">سُورَةُ {surah_name}</div>
  <div class="reciter">بصوت القارئ {reciter_name}</div>
  <div class="sub">{sub_title}</div>
</div></body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([
        chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", 
        "--window-size=1080,1920", f"--screenshot={os.path.abspath(out_cover)}", 
        f"file://{os.path.abspath(h_path)}"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): 
        os.remove(h_path)
    return out_cover

def build_fast_short_video(surah_num, surah_name, start_a, end_a, badge_label, reciter_info, tag):
    font_b64 = get_font_base64()
    rec_name = reciter_info["name"]

    aud_file = f"aud_seg_{tag}.mp3"
    download_surah_segment(surah_num, start_a, end_a, reciter_info, aud_file)
    audio_clip = AudioFileClip(aud_file)

    if audio_clip.duration > 48.0:
        audio_clip = audio_clip.subclip(0, 48.0)

    full_text_list = []
    for a in range(start_a, end_a + 1):
        try:
            t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=10).json()
            txt = clean_arabic(t_res.get("data", {}).get("text", ""))
            if a == 1 and surah_num != 1:
                txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()
            full_text_list.append(txt)
        except Exception:
            continue

    combined_text = " ۝ ".join(full_text_list)
    words = combined_text.split()
    tot_chars = sum(len(w) for w in words) if words else 1

    text_clips = []
    w_start = 0.0
    for idx, w in enumerate(words):
        w_dur = (len(w) / tot_chars) * audio_clip.duration
        if w_start + w_dur > 48.5:
            break
        frame_img = render_quran_frame(words, idx, badge_label, font_b64)
        text_clips.append(ImageClip(frame_img).set_start(w_start).set_duration(w_dur).set_position(("center", "center")))
        w_start += w_dur

    tot_dur = audio_clip.duration
    audio_clip = audio_clip.set_duration(tot_dur)

    raw_bg = f"raw_bg_{tag}.mp4"
    fast_bg = f"fast_bg_{tag}.mp4"
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=nature+vertical+cinematic&orientation=portrait&per_page=15", headers=headers, timeout=15).json()
    v_link = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))[-1]["link"]
    
    with open(raw_bg, "wb") as f:
        f.write(requests.get(v_link, timeout=35).content)

    scale_cmd = [
        "ffmpeg", "-y", "-i", raw_bg,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-an", fast_bg
    ]
    subprocess.run(scale_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(raw_bg): 
        os.remove(raw_bg)

    bg = VideoFileClip(fast_bg)
    bg = (bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur))
    dim = ColorClip(size=(1080, 1920), color=(10, 15, 20)).set_opacity(0.32).set_duration(tot_dur)

    main_video = CompositeVideoClip([bg, dim] + text_clips).set_audio(audio_clip).set_duration(tot_dur)

    cover_file = f"cover_{tag}.jpg"
    generate_cover_file(surah_name, f"الآيات ({start_a}-{end_a})", rec_name, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.10)

    temp_joined = f"temp_{tag}.mp4"
    joined = concatenate_videoclips([cover_clip, main_video])
    joined.write_videofile(temp_joined, fps=24, codec="libx264", audio_codec="aac", bitrate="2500k", threads=4, preset="ultrafast")

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

    if os.path.exists(aud_file): 
        os.remove(aud_file)
    if os.path.exists(fast_bg): 
        os.remove(fast_bg)
    if os.path.exists(temp_joined) and temp_joined != out_file: 
        os.remove(temp_joined)

    return out_file, cover_file, rec_name

def upload_files(video_file):
    print("📤 رفع ملف Shorts للحصول على رابط مباشر...", flush=True)
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
            print(f"❌ فشل نشر الفيديو في Dailymotion: {create_res}", flush=True)

    except Exception as e:
        print(f"⚠️ خطأ أثناء النشر على Dailymotion: {e}", flush=True)

    return None

def post_to_odysee(remote_video_url, title, description, tags=None):
    if tags is None:
        tags = ["quran", "islam", "shorts", "reels"]

    auth_token = os.getenv("ODYSEE_AUTH_TOKEN", "").strip()
    if not auth_token or not remote_video_url:
        print("⚠️ بيانات Odysee أو رابط الفيديو غير مكتمل، تم التخطي.", flush=True)
        return None

    try:
        print("🚀 جاري نشر الفيديو مباشرة إلى منصة Odysee عبر Remote URL...", flush=True)
        clean_stream_name = f"quran-short-{int(time.time())}"
        headers = {
            "Content-Type": "application/json-rpc",
            "X-Lbry-Auth-Token": auth_token
        }
        api_url = f"https://api.na-backend.odysee.com/api/v1/proxy?m=publish&auth_token={auth_token}"

        # فحص وجود قنوات معتمدة في الحساب واستخدام المعرف الخاص بها
        channel_id = None
        try:
            ch_res = requests.post(
                f"https://api.na-backend.odysee.com/api/v1/proxy?m=channel_list&auth_token={auth_token}",
                headers=headers,
                json={"jsonrpc": "2.0", "method": "channel_list", "params": {"auth_token": auth_token}, "id": 1},
                timeout=15
            ).json()
            channels = ch_res.get("result", {}).get("items", [])
            if channels:
                channel_id = channels[0].get("claim_id")
                print(f"📡 القناة المعتمدة: {channels[0].get('name')}", flush=True)
        except Exception:
            channel_id = None

        publish_params = {
            "auth_token": auth_token,
            "name": clean_stream_name,
            "title": title[:95],
            "description": description,
            "tags": tags,
            "languages": ["ar"],
            "bid": "0.0001",
            "remote_url": remote_video_url
        }

        if channel_id:
            publish_params["channel_id"] = channel_id

        payload = {
            "jsonrpc": "2.0",
            "method": "publish",
            "params": publish_params,
            "id": int(time.time())
        }

        pub_res = requests.post(api_url, headers=headers, json=payload, timeout=60).json()

        claim_info = pub_res.get("result", {}).get("outputs", [{}])[0]
        claim_name = claim_info.get("name")
        claim_id = claim_info.get("claim_id")

        if claim_name and claim_id:
            odysee_url = f"https://odysee.com/{claim_name}:{claim_id}"
            print(f"✅ تم النشر بنجاح على Odysee: {odysee_url}", flush=True)
            return odysee_url
        else:
            print(f"❌ رد النشر من Odysee: {pub_res}", flush=True)

    except Exception as e:
        print(f"⚠️ استثناء أثناء النشر على Odysee: {e}", flush=True)

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

if __name__ == "__main__":
    now_utc = datetime.datetime.utcnow()
    is_friday = (now_utc.weekday() == 4)
    reciter = random.choice(RECITERS_POOL)
    history = load_history()

    if is_friday:
        week_str = now_utc.strftime("%Y_%U")
        item = get_friday_kahf_chunk(history, week_str)
        print(f"🌟 يوم الجمعة المبارك: إنتاج سورة الكهف (جزء {item['part']}) - الآيات ({item['start']}-{item['end']})...", flush=True)
        yt_title = f"سورة الكهف كاملة (جزء {item['part']}) الآيات ({item['start']}-{item['end']}) | نور الجمعة 🤍 #shorts"
        caption = (
            f"🕌 سورة الكهف - الجزء {item['part']}\n"
            f"✨ الآيات الكريمة: ({item['start']} - {item['end']})\n"
            f"🎙️ بصوت القارئ: {reciter['name']}\n\n"
            f"قال ﷺ: (من قرأ سورة الكهف في يوم الجمعة أضاء له من النور ما بين الجمعتين) 🌿\n\n"
            f"#سورة_الكهف #يوم_الجمعة #جمعة_مباركة #قرآن #shorts #reels"
        )
    else:
        item = pick_unposted_clip_all_quran(history)
        print(f"🎬 اختيار مقطع Shorts من القرآن: سورة {item['name']} الآيات ({item['start']}-{item['end']})...", flush=True)
        yt_title = f"تلاوة خاشعة | سورة {item['name']} ({item['start']}-{item['end']}) 🤍 #shorts"
        caption = (
            f"📖 سورة {item['name']} | الآيات ({item['start']} - {item['end']})\n"
            f"🎙️ بصوت القارئ: {reciter['name']}\n\n"
            f"اللهم اجعل القرآن ربيع قلوبنا ونور صدورنا وجلاء أحزاننا 🤍\n\n"
            f"#سورة_{item['name']} #قرآن #shorts #reels #تلاوة_خاشعة"
        )

    tag = f"short_{item['key']}_{int(time.time())}"

    vid_file, cov_file, r_name = build_fast_short_video(
        item["surah"], item["name"], item["start"], item["end"],
        item["badge"], reciter, tag
    )

    # 1. رفع المقطع وإنشاء الرابط المباشر
    pub_url = upload_files(vid_file)

    # 2. النشر على منصات Buffer (YouTube و Instagram)
    if pub_url:
        post_to_buffer(pub_url, yt_title, caption)
    else:
        print("❌ فشل الحصول على رابط تحميل للفيديو، لم يتم الإرسال لـ Buffer.", flush=True)

    # 3. النشر المباشر على Dailymotion
    dm_link = post_to_dailymotion(vid_file, yt_title, caption)

    # 4. النشر المباشر على Odysee
    odysee_link = post_to_odysee(pub_url, yt_title, caption) if pub_url else None

    if not is_friday:
        if item["key"] not in history["posted_keys"]:
            history["posted_keys"].append(item["key"])

    save_history(history)

    # 5. إرسال التقرير النهائي إلى Telegram
    dm_report = f"\n📺 <b>Dailymotion:</b> <a href='{dm_link}'>مشاهدة على ديلي موشن</a>" if dm_link else ""
    odysee_report = f"\n🎥 <b>Odysee:</b> <a href='{odysee_link}'>مشاهدة على أوديسي</a>" if odysee_link else ""
    report = (
        f"✨ <b>تم إنتاج ونشر مقطع Shorts جديد بنجاح!</b>\n\n"
        f"📖 <b>السورة:</b> {item['name']} " + (f"(جزء {item['part']})" if item.get("part") else "") + f"\n"
        f"🔢 <b>الآيات:</b> ({item['start']} إلى {item['end']})\n"
        f"🎙️ <b>القارئ:</b> {r_name}\n"
        f"⏱️ <b>النوع:</b> فيديو طولي 9:16 بكلمات مذهبة متحركة\n"
        f"🔒 <b>كود السجل:</b> <code>{item['key']}</code>\n"
        f"🔗 <b>الرابط الأصلي:</b> <a href='{pub_url}'>تحميل المقطع</a>"
        f"{dm_report}"
        f"{odysee_report}"
    )
    notify_telegram(report, cov_file)

    if os.path.exists(vid_file): 
        os.remove(vid_file)
    if os.path.exists(cov_file): 
        os.remove(cov_file)
    print("=== اكتمل الرندر للشورتس، التحديث، والنشر بنجاح ===", flush=True)

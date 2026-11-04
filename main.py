import os
import sys
import json
import time
import base64
import random
import shutil
import datetime
import subprocess
import requests

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None).LANCZOS if hasattr(PIL.Image, 'Resampling') else None)

from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)

HISTORY_FILE = "history_shorts_all.json"
QURAN_FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf"

RECITERS_POOL = [
    {"name": "محمد صديق المنشاوي", "id": "ar.minshawi"},
    {"name": "ياسر الدوسري", "id": "ar.yasseraldossari"}
]

# ----------------- عقل الذكاء الاصطناعي (OpenAI المخرج) -----------------
def generate_ai_director_plan(surah_name, start_a, end_a, reciter_name):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "dark cinematic rain street", f"تلاوة خاشعة | سورة {surah_name}", "#القرآن #shorts"

    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"""
    أنت مخرج سينمائي وخبير يوتيوب SEO إسلامي. المقطع الحالي: سورة {surah_name} (الآيات {start_a} إلى {end_a}) بصوت {reciter_name}.
    المطلوب منك 3 أشياء بصيغة JSON فقط:
    1. "bg_query": كلمة بحث قصيرة جداً بالإنجليزية لجلب فيديو خلفية مناسب لمعنى السورة (مثلاً: dark moody rain, stormy sea, calm nature, islamic architecture).
    2. "title": عنوان يوتيوب قوي وجذاب (أقل من 90 حرف).
    3. "description": وصف للفيديو يحتوي على هاشتاجات قوية تتصدر التريند.
    لا تكتب أي شيء خارج الـ JSON.
    """

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        content = json.loads(res.json()['choices'][0]['message']['content'])
        return content.get("bg_query", "cinematic dark rain"), content.get("title"), content.get("description")
    except Exception as e:
        print(f"⚠️ فشل الذكاء الاصطناعي، تفعيل الوضع الافتراضي: {e}", flush=True)
        return "dark cinematic rain", f"تلاوة خاشعة | سورة {surah_name} 🤍", f"#القرآن_الكريم #سورة_{surah_name}"

# ----------------- وظائف معالجة الفيديو والتزامن -----------------
def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ']: text = text.replace(s, '')
    return text.strip()

def to_arabic_num(num):
    arabic_digits = {'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'}
    return "".join(arabic_digits.get(c, c) for c in str(num))

def get_font_base64():
    if not os.path.exists("Amiri-Regular.ttf"):
        with open("Amiri-Regular.ttf", "wb") as f: f.write(requests.get(QURAN_FONT_URL).content)
    with open("Amiri-Regular.ttf", "rb") as f: return base64.b64encode(f.read()).decode("ascii")

def prepare_ai_background(bg_query, tag):
    raw_bg = f"raw_bg_{tag}.mp4"
    fast_bg = f"ready_bg_{tag}.mp4"
    
    print(f"🎬 المخرج (AI) طلب خلفية بنمط: '{bg_query}'... جاري البحث في Pexels", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    p_headers = {"Authorization": pexels_key} if pexels_key else {}
    success = False

    try:
        api_url = f"https://api.pexels.com/videos/search?query={bg_query}&orientation=portrait&per_page=10"
        r = requests.get(api_url, headers=p_headers, timeout=15).json()
        videos = r.get("videos", [])
        if videos:
            v = random.choice(videos)
            hd_file = sorted(v.get("video_files", []), key=lambda x: x.get("width", 0))[-1]
            with open(raw_bg, "wb") as f: f.write(requests.get(hd_file.get("link"), timeout=60).content)
            success = True
    except Exception:
        pass

    if not success or not os.path.exists(raw_bg):
        print("⚠️ فشل جلب فيديو من Pexels، جاري استخدام الخلفية الاحتياطية...", flush=True)
        fallback_url = "https://videos.pexels.com/video-files/2491294/2491294-hd_1080_1920_30fps.mp4"
        with open(raw_bg, "wb") as f: f.write(requests.get(fallback_url, timeout=60).content)

    subprocess.run([
        "ffmpeg", "-y", "-i", raw_bg,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-b:v", "6000k", "-an", fast_bg
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(raw_bg): os.remove(raw_bg)
    return fast_bg

def render_lower_verse_frame(verse_text, timer_str, idx, font_b64):
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
    <style>@font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
    body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; font-family: 'Amiri', serif; padding-bottom: 310px; }}
    .verse-box {{ text-align: center; color: #FFFFFF; font-size: 56px; max-width: 900px; padding: 0 40px; text-shadow: 0 2px 10px rgba(0,0,0,0.95), 0 4px 25px rgba(0,0,0,0.85); line-height: 1.8;}}
    .timer {{ margin-top: 15px; font-family: sans-serif; font-size: 26px; color: rgba(255,255,255,0.7); }}</style></head>
    <body><div class="verse-box">{verse_text}</div><div class="timer">{timer_str}</div></body></html>"""
    h_path, p_path = f"tmp_{idx}.html", f"frame_{idx}.png"
    with open(h_path, "w", encoding="utf-8") as f: f.write(html)
    subprocess.run(["google-chrome", "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): os.remove(h_path)
    return p_path

def build_ai_video(surah_num, surah_name, start_a, end_a, reciter_info, bg_query, tag):
    font_b64 = get_font_base64()
    audio_clips, video_clips, temp_files = [], [], []
    current_time = 0.0

    print("📥 سحب وضبط تزامن الآيات برمجياً...", flush=True)
    for a in range(start_a, end_a + 1):
        try:
            req = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/{reciter_info['id']}", timeout=15)
            if req.status_code != 200:
                print(f"⚠️ تخطي الآية {a} لعدم استجابة السيرفر.", flush=True)
                continue
                
            res = req.json()
            data = res.get("data")
            
            # حماية النظام من خطأ String Indices
            if not isinstance(data, dict) or "audio" not in data or "text" not in data:
                print(f"⚠️ بيانات الآية {a} غير مكتملة أو تالفة، تم التخطي.", flush=True)
                continue
                
            aud_file = f"aud_{a}_{tag}.mp3"
            with open(aud_file, "wb") as f: 
                f.write(requests.get(data["audio"], timeout=30).content)
            temp_files.append(aud_file)
            
            text = clean_arabic(data["text"])
            if a == 1 and surah_num != 1: text = text.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()
            
            a_clip = AudioFileClip(aud_file)
            mins, secs = int(current_time // 60), int(current_time % 60)
            
            frame_path = render_lower_verse_frame(f"{text} ﴿{to_arabic_num(a)}﴾", f"{mins:02d}:{secs:02d}", f"{a}_{tag}", font_b64)
            temp_files.append(frame_path)
            
            audio_clips.append(a_clip)
            video_clips.append(ImageClip(frame_path).set_duration(a_clip.duration))
            current_time += a_clip.duration
            
        except Exception as e:
            print(f"⚠️ خطأ في معالجة الآية {a}: {e}", flush=True)
            continue

    if not audio_clips:
        raise Exception("❌ لم يتم جلب أي آيات بنجاح بسبب خلل في سيرفرات القرآن.")

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = final_audio.duration
    
    fast_bg = prepare_ai_background(bg_query, tag)
    temp_files.append(fast_bg)
    
    bg = VideoFileClip(fast_bg)
    bg = bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)
    dim = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_opacity(0.18).set_duration(tot_dur)
    
    text_seq = concatenate_videoclips(video_clips).set_position(("center", "bottom"))
    main_video = CompositeVideoClip([bg, dim, text_seq]).set_audio(final_audio).set_duration(tot_dur)

    out_file = f"final_{tag}.mp4"
    main_video.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac", bitrate="6000k", threads=4, preset="medium")
    
    for tf in temp_files:
        if os.path.exists(tf): 
            try: os.remove(tf)
            except: pass
    return out_file

# ----------------- بقية دوال الرفع والنشر -----------------
def upload_files(video_file):
    try:
        with open(video_file, "rb") as f:
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=120)
            if r.status_code == 200 and r.text.startswith("http"): return r.text.strip()
    except: return None

def post_to_dailymotion(video_file, title, description, tags):
    api_key = os.getenv("DAILYMOTION_KEY", "").strip()
    if not api_key: return None
    try:
        token_res = requests.post("https://api.dailymotion.com/oauth/token", data={"grant_type": "password", "client_id": api_key, "client_secret": os.getenv("DAILYMOTION_SECRET"), "username": os.getenv("DAILYMOTION_USERNAME"), "password": os.getenv("DAILYMOTION_PASSWORD"), "scope": "manage_videos"}).json()
        headers = {"Authorization": f"Bearer {token_res.get('access_token')}"}
        up_url = requests.get("https://api.dailymotion.com/file/upload", headers=headers).json().get("upload_url")
        with open(video_file, "rb") as f: file_url = requests.post(up_url, files={"file": f}).json().get("url")
        vid_id = requests.post("https://api.dailymotion.com/me/videos", headers=headers, data={"url": file_url, "title": title[:250], "description": description, "tags": tags, "published": "true"}).json().get("id")
        return f"https://www.dailymotion.com/video/{vid_id}" if vid_id else None
    except: return None

def notify_telegram(message):
    try:
        requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", json={"chat_id": os.getenv("ADMIN_CHAT_ID"), "text": message, "parse_mode": "HTML"})
    except: pass

# ----------------- تشغيل المنظومة الرئيسية -----------------
if __name__ == "__main__":
    reciter = random.choice(RECITERS_POOL)
    
    surahs = requests.get("https://api.alquran.cloud/v1/meta").json()["data"]["surahs"]["references"]
    surah = random.choice([s for s in surahs if s["numberOfAyahs"] >= 3 and s["number"] != 18])
    start_a = random.randint(1, max(1, surah["numberOfAyahs"] - 2))
    end_a = min(surah["numberOfAyahs"], start_a + 2)
    tag = f"ai_vid_{int(time.time())}"

    print(f"🤖 الذكاء الاصطناعي بدأ العمل على سورة {surah['name']}...", flush=True)
    
    bg_query, yt_title, caption = generate_ai_director_plan(surah["name"], start_a, end_a, reciter["name"])
    
    try:
        vid_file = build_ai_video(surah["number"], surah["name"], start_a, end_a, reciter, bg_query, tag)
    except Exception as e:
        print(e, flush=True)
        sys.exit(1)
    
    pub_url = upload_files(vid_file)
    dm_link = post_to_dailymotion(vid_file, yt_title, caption, "quran,islam,shorts")
    
    report = f"✨ <b>الذكاء الاصطناعي أتم المهمة بنجاح!</b>\n\n📖 <b>السورة:</b> {surah['name']} ({start_a}-{end_a})\n🎙️ <b>القارئ:</b> {reciter['name']}\n🧠 <b>بحث الخلفية:</b> <code>{bg_query}</code>\n📝 <b>العنوان:</b> {yt_title}\n\n🔗 <b>رابط التحميل:</b> <a href='{pub_url}'>هنا</a>\n📺 <b>ديلي موشن:</b> <a href='{dm_link}'>هنا</a>"
    notify_telegram(report)
    
    if os.path.exists(vid_file): os.remove(vid_file)

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

# ترقيع توافق Pillow مع MoviePy
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None).LANCZOS if hasattr(PIL.Image, 'Resampling') else None)

from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, 
    CompositeVideoClip, ColorClip, concatenate_audioclips, concatenate_videoclips
)

HISTORY_FILE = "history.json"
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

RECITERS_POOL = [
    {"id": "Minshawy_Murattal_128kbps", "name": "محمد صديق المنشاوي"},
    {"id": "Husary_128kbps", "name": "محمود خليل الحصري"}
]

# ----------------- 1. نظام منع التكرار الدائم (History Tracker) -----------------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"posted_keys": []}
    return {"posted_keys": []}

def save_history(clip_key):
    history = load_history()
    if clip_key not in history["posted_keys"]:
        history["posted_keys"].append(clip_key)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ----------------- 2. جلب وتوليد مقطع عشوائي جديد من الـ 114 سورة -----------------
def get_all_surahs_meta():
    """جلب بيانات كل سور القرآن الـ 114 (الاسم وعدد الآيات)"""
    cache_path = "surahs_meta.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        r = requests.get("https://api.alquran.cloud/v1/meta", timeout=15).json()
        surahs = r.get("data", {}).get("surahs", {}).get("references", [])
        meta = [{"number": s["number"], "name": s["name"].replace("سُورَةُ ", "").strip(), "ayahs": s["numberOfAyahs"]} for s in surahs]
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        return meta
    except Exception:
        # احتياطي لأشهر السور في حال انقطاع واجهة meta
        return [{"number": 1, "name": "الفاتحة", "ayahs": 7}, {"number": 18, "name": "الكهف", "ayahs": 110}, {"number": 67, "name": "الملك", "ayahs": 30}]

def pick_unposted_random_clip():
    """اختيار مقطع عشوائي لم يسبق نشره نهائياً"""
    surahs = get_all_surahs_meta()
    history = load_history()
    posted_keys = set(history.get("posted_keys", []))

    # تجربة اختيار عشوائي بحد أقصى 150 محاولة لمنع أي تكرار
    for _ in range(150):
        surah = random.choice(surahs)
        s_num = surah["number"]
        s_name = surah["name"]
        total_ayahs = surah["ayahs"]

        # تحديد عدد الآيات المناسب ليكون الفيديو أقل من دقيقة
        # السور الطويلة آياتها طويلة (نختار من 2 إلى 4 آيات)، والقصيرة (نختار من 4 إلى 7)
        chunk_size = random.randint(2, 4) if total_ayahs > 40 else random.randint(3, min(6, total_ayahs))
        if total_ayahs <= 5:
            start_a = 1
            end_a = total_ayahs
        else:
            start_a = random.randint(1, max(1, total_ayahs - chunk_size + 1))
            end_a = min(total_ayahs, start_a + chunk_size - 1)

        clip_key = f"{s_num}_{start_a}_{end_a}"
        if clip_key not in posted_keys:
            return {
                "surah": s_num,
                "name": s_name,
                "start": start_a,
                "end": end_a,
                "key": clip_key,
                "badge": f"سورة {s_name} 🌿"
            }

    # إذا استنفذت المحاولات العشوائية، يختار أول نطاق غير مسجل في التاريخ بالتسلسل
    for surah in surahs:
        s_num = surah["number"]
        for st in range(1, surah["ayahs"], 3):
            en = min(surah["ayahs"], st + 2)
            k = f"{s_num}_{st}_{en}"
            if k not in posted_keys:
                return {"surah": s_num, "name": surah["name"], "start": st, "end": en, "key": k, "badge": f"سورة {surah['name']} 🌿"}

    return {"surah": 1, "name": "الفاتحة", "start": 1, "end": 7, "key": f"1_1_7_{int(time.time())}", "badge": "الفاتحة 🤍"}

# ----------------- 3. المعالجة البصرية وهندسة الصوت المضادة للحقوق -----------------
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
    audio_filter = "aresample=44100,asetrate=44100*1.015,atempo=0.985,aecho=0.8:0.7:28:0.2,volume=1.05"
    cmd = ["ffmpeg", "-y", "-i", raw_audio, "-af", audio_filter, "-b:a", "192k", out_audio]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_audio

def download_ayah_safe(surah_num, ayah_num, rec_id, out_file):
    s_str, a_str = f"{surah_num:03d}", f"{ayah_num:03d}"
    raw_tmp = f"raw_{s_str}_{a_str}.mp3"
    urls = [
        f"https://everyayah.com/data/{rec_id}/{s_str}{a_str}.mp3",
        f"https://everyayah.com/data/Minshawy_Murattal_128kbps/{s_str}{a_str}.mp3",
        f"https://everyayah.com/data/Husary_128kbps/{s_str}{a_str}.mp3"
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=20)
            if r.status_code == 200 and len(r.content) > 4000 and not r.content.startswith(b"<!DOCTYPE"):
                with open(raw_tmp, "wb") as f:
                    f.write(r.content)
                apply_anti_copyright(raw_tmp, out_file)
                if os.path.exists(raw_tmp): os.remove(raw_tmp)
                return True
        except Exception:
            continue
    return False

def render_quran_frame(words, active_idx, badge_text, font_b64):
    chrome_bin = get_chrome()
    words_html = []
    for i, w in enumerate(words):
        if i == active_idx:
            words_html.append(f'<span style="color:#D4AF37; transform:scale(1.08); text-shadow:0 0 16px rgba(212,175,55,0.95);">{w}</span>')
        else:
            words_html.append(f'<span style="color:#FFFFFF; text-shadow:0 0 10px rgba(0,0,0,0.95);">{w}</span>')

    full_verse = " ".join(words_html)
    font_size = 68 if len(words) <= 7 else (52 if len(words) <= 14 else 42)

    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: transparent; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }}
  .badge {{ position: absolute; top: 190px; background: rgba(10,14,20,0.7); border: 1px solid rgba(212,175,55,0.45); color: #fff; font-family: 'Amiri'; font-size: 26px; padding: 10px 28px; border-radius: 30px; }}
  .ayah {{ direction: rtl; text-align: center; font-family: 'Amiri'; font-size: {font_size}px; font-weight: bold; line-height: 1.95; max-width: 930px; margin: auto 0; }}
  .watermark {{ position: absolute; bottom: 110px; left: 50%; transform: translateX(-50%); font-family: 'Amiri'; font-size: 24px; color: rgba(255,255,255,0.45); direction: ltr; }}
</style></head>
<body>
  <div class="badge">🎧 {badge_text} 🌿</div>
  <div class="ayah">{full_verse}</div>
  <div class="watermark">@quran_reels</div>
</body></html>"""

    h_path, p_path = f"tmp_{active_idx}.html", f"frame_{active_idx}.png"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", "--default-background-color=00000000", f"--screenshot={os.path.abspath(p_path)}", f"file://{os.path.abspath(h_path)}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): os.remove(h_path)
    return p_path

def generate_cover_file(surah_name, sub_title, reciter_name, font_b64, out_cover):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ width: 1080px; height: 1920px; background: radial-gradient(circle at center, #151d28 0%, #0a0d13 100%); display: flex; justify-content: center; align-items: center; position: relative; }}
  .box {{ width: 1080px; height: 1080px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
  .circle {{ position: absolute; width: 780px; height: 780px; border-radius: 50%; border: 2px solid rgba(212, 175, 55, 0.45); }}
  .badge {{ font-family: 'Amiri'; font-size: 26px; color: #fff; background: rgba(0,0,0,0.5); padding: 8px 24px; border-radius: 20px; border: 1px solid rgba(212,175,55,0.3); margin-bottom: 20px; z-index: 2; }}
  .title {{ font-family: 'Amiri'; font-size: 82px; font-weight: bold; color: #D4AF37; margin-bottom: 15px; z-index: 2; text-shadow: 0 0 20px rgba(212,175,55,0.8); }}
  .reciter {{ font-family: 'Amiri'; font-size: 38px; color: #fff; z-index: 2; margin-bottom: 15px; }}
  .sub {{ font-family: 'Amiri'; font-size: 26px; color: rgba(212,175,55,0.9); z-index: 2; }}
</style></head>
<body><div class="box">
  <div class="circle"></div>
  <div class="badge">🕌 تلاوة خاشعة بالذهب 🌿</div>
  <div class="title">سُورَةُ {surah_name}</div>
  <div class="reciter">بصوت القارئ {reciter_name}</div>
  <div class="sub">{sub_title}</div>
</div></body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", "--window-size=1080,1920", f"--screenshot={os.path.abspath(out_cover)}", f"file://{os.path.abspath(h_path)}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): os.remove(h_path)
    return out_cover

def build_fast_short_video(surah_num, surah_name, start_a, end_a, badge_label, reciter_info, tag):
    rec_id = reciter_info["id"]
    rec_name = reciter_info["name"]
    font_b64 = get_font_base64()

    ayahs = []
    for a in range(start_a, end_a + 1):
        t_res = requests.get(f"https://api.alquran.cloud/v1/ayah/{surah_num}:{a}/quran-simple", timeout=15).json()
        txt = clean_arabic(t_res.get("data", {}).get("text", ""))
        if a == 1 and surah_num != 1:
            txt = txt.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").strip()

        aud_file = f"aud_{tag}_{a}.mp3"
        download_ayah_safe(surah_num, a, rec_id, aud_file)
        ayahs.append({"text": txt, "audio": aud_file})

    audio_clips, text_clips = [], []
    curr_t = 0.0

    for ay in ayahs:
        ac = AudioFileClip(ay["audio"])
        audio_clips.append(ac)
        words = ay["text"].split()
        tot_chars = sum(len(w) for w in words)
        w_start = curr_t
        for idx, w in enumerate(words):
            w_dur = (len(w) / tot_chars) * ac.duration
            frame_img = render_quran_frame(words, idx, badge_label, font_b64)
            text_clips.append(ImageClip(frame_img).set_start(w_start).set_duration(w_dur).set_position(("center", "center")))
            w_start += w_dur
        curr_t += ac.duration

    final_audio = concatenate_audioclips(audio_clips)
    tot_dur = curr_t + 0.8

    # جلب وتحجيم الفيديو بسرعة عبر ffmpeg في ثانيتين
    raw_bg = f"raw_bg_{tag}.mp4"
    fast_bg = f"fast_bg_{tag}.mp4"
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    headers = {"Authorization": pexels_key} if pexels_key else {}
    res = requests.get("https://api.pexels.com/videos/search?query=scenic+nature+drone+vertical&orientation=portrait&per_page=12", headers=headers, timeout=15).json()
    v_link = sorted(random.choice(res.get("videos", []))["video_files"], key=lambda x: x.get("width", 0))[-1]["link"]
    
    with open(raw_bg, "wb") as f:
        f.write(requests.get(v_link, timeout=35).content)

    scale_cmd = [
        "ffmpeg", "-y", "-i", raw_bg,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-an", fast_bg
    ]
    subprocess.run(scale_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(raw_bg): os.remove(raw_bg)

    bg = VideoFileClip(fast_bg)
    bg = (bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur))
    dim = ColorClip(size=(1080, 1920), color=(10, 15, 20)).set_opacity(0.32).set_duration(tot_dur)

    main_video = CompositeVideoClip([bg, dim] + text_clips).set_audio(final_audio)

    cover_file = f"cover_{tag}.jpg"
    generate_cover_file(surah_name, f"الآيات ({start_a}-{end_a})", rec_name, font_b64, cover_file)
    cover_clip = ImageClip(cover_file).set_duration(0.12)

    temp_joined = f"temp_{tag}.mp4"
    joined = concatenate_videoclips([cover_clip, main_video])
    joined.write_videofile(temp_joined, fps=24, codec="libx264", audio_codec="aac", bitrate="2000k", threads=4, preset="ultrafast")

    out_file = f"final_{tag}.mp4"
    embed_cmd = ["ffmpeg", "-y", "-i", temp_joined, "-i", cover_file, "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic", out_file]
    try:
        subprocess.run(embed_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        out_file = temp_joined

    for ay in ayahs:
        if os.path.exists(ay["audio"]): os.remove(ay["audio"])
    if os.path.exists(fast_bg): os.remove(fast_bg)
    if os.path.exists(temp_joined) and temp_joined != out_file: os.remove(temp_joined)

    return out_file, cover_file, rec_name

def upload_files(video_file, cover_file):
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if repo and gh_token:
        for _ in range(3):
            tag_name = f"v{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
            try:
                res = requests.post(
                    f"https://api.github.com/repos/{repo}/releases",
                    headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
                    json={"tag_name": tag_name, "name": f"Release {tag_name}", "draft": False}, timeout=20
                ).json()
                if "upload_url" in res:
                    u_url = res["upload_url"].split("{")[0]
                    with open(video_file, "rb") as vf:
                        up_res = requests.post(f"{u_url}?name=video.mp4", headers={"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}, data=vf, timeout=90).json()
                    return up_res.get("browser_download_url")
            except Exception:
                time.sleep(1)

    try:
        with open(video_file, "rb") as f:
            r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=90).json()
            if r.get("status") == "success":
                return r["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass
    return None

def post_to_buffer(video_url, yt_title, caption):
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channels_raw = os.getenv("BUFFER_CHANNEL_ID", "").strip()
    if not buffer_token or not channels_raw:
        return
    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
    graphql_url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {buffer_token}", "Content-Type": "application/json"}
    mutation = """mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id } } ... on MutationError { message } } }"""

    for ch_id in channel_ids:
        post_input = {
            "channelId": ch_id, "text": caption, "mode": "shareNow", "schedulingType": "automatic",
            "assets": [{"video": {"url": video_url}}]
        }
        if ch_id in ["6aa9df26ea19ca0bde51b3c5", "6aa72b30ea19ca0bde39598b"]:
            post_input["metadata"] = {"youtube": {"title": yt_title[:65], "categoryId": "27"}}
        elif ch_id == "6aa6d1fbea19ca0bde35e91c":
            post_input["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}

        try:
            requests.post(graphql_url, headers=headers, json={"query": mutation, "variables": {"input": post_input}}, timeout=30)
        except Exception:
            pass

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

# ----------------- الدالة الرئيسية -----------------
if __name__ == "__main__":
    now_utc = datetime.datetime.utcnow()
    is_friday = (now_utc.weekday() == 4 and 9 <= now_utc.hour <= 14)
    reciter = random.choice(RECITERS_POOL)

    if is_friday:
        item = {"surah": 18, "name": "الكهف", "start": 1, "end": 6, "badge": "نور ما بين الجمعتين 🌿", "key": f"friday_kahf_{now_utc.strftime('%Y%U')}"}
    else:
        item = pick_unposted_random_clip()

    tag = f"q_{item['key']}_{int(time.time())}"
    print(f"🎬 اختيار مقطع جديد كلياً: سورة {item['name']} الآيات ({item['start']}-{item['end']})...", flush=True)

    vid_file, cov_file, r_name = build_fast_short_video(
        item["surah"], item["name"], item["start"], item["end"],
        f"سورة {item['name']} • تلاوة خاشعة", reciter, tag
    )

    yt_title = f"تلاوة خاشعة | سورة {item['name']} ({item['start']}-{item['end']}) 🤍 #shorts"
    caption = (
        f"📖 سورة {item['name']} | الآيات ({item['start']} - {item['end']})\n"
        f"🎙️ بصوت القارئ: {r_name}\n\n"
        f"اللهم اجعل القرآن ربيع قلوبنا ونور صدورنا 🤍\n\n"
        f"#سورة_{item['name']} #قرآن #راحة_نفسية #shorts #reels"
    )

    pub_url = upload_files(vid_file, cov_file)
    if pub_url:
        post_to_buffer(pub_url, yt_title, caption)

    # حفظ المقطع فوراً في السجل الدائم لمنع تكراره مستقبلاً
    save_history(item["key"])

    report = (
        f"✨ <b>تم إنتاج ونشر مقطع جديد وحصري!</b>\n\n"
        f"📖 <b>السورة:</b> {item['name']} ({item['start']}-{item['end']})\n"
        f"🎙️ <b>القارئ:</b> {r_name}\n"
        f"🔒 <b>كود السجل:</b> <code>{item['key']}</code> (ممنوع تكراره)\n"
        f"🔗 <b>الرابط:</b> <a href='{pub_url}'>مشاهدة المقطع</a>"
    )
    notify_telegram(report, cov_file)

    if os.path.exists(vid_file): os.remove(vid_file)
    if os.path.exists(cov_file): os.remove(cov_file)
    print("=== اكتمل الرندر وحفظ السجل بنجاح ===", flush=True)

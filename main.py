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

QURAN_FONT_URL = "https://" + "cdn.jsdelivr.net" + "/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf"

RECITERS_POOL = [
    {"name": "محمد صديق المنشاوي", "id": "ar.minshawi", "everyayah": "Minshawy_Murattal_128kbps"},
    {"name": "ياسر الدوسري", "id": "ar.yasseraldossari", "everyayah": "Yasser_Ad-Dussary_128kbps"}
]

def generate_ai_director_plan(surah_name, start_a, end_a, reciter_name):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("⚠️ مفتاح GEMINI_API_KEY غير موجود، استخدام الوضع الافتراضي.", flush=True)
        return "dark cinematic rain", f"تلاوة خاشعة | سورة {surah_name}", f"#القرآن_الكريم #سورة_{surah_name}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    أنت مخرج سينمائي وخبير يوتيوب SEO إسلامي. المقطع الحالي: سورة {surah_name} (الآيات {start_a} إلى {end_a}) بصوت {reciter_name}.
    المطلوب منك 3 أشياء بصيغة JSON فقط:
    1. "bg_query": كلمة بحث قصيرة جداً بالإنجليزية لجلب فيديو خلفية مناسب لمعنى السورة (مثلاً: dark moody rain, stormy sea, calm nature, islamic architecture).
    2. "title": عنوان يوتيوب قوي وجذاب (أقل من 90 حرف).
    3. "description": وصف للفيديو يحتوي على هاشتاجات قوية تتصدر التريند.
    لا تكتب أي شيء خارج الـ JSON.
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7}
    }

    try:
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        if res.status_code == 200:
            data = res.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                
            content = json.loads(raw_text)
            return content.get("bg_query", "cinematic dark rain"), content.get("title", f"تلاوة خاشعة | سورة {surah_name}"), content.get("description", f"#القرآن_الكريم #سورة_{surah_name}")
        else:
            print(f"⚠️ خطأ من Gemini API: {res.text}", flush=True)
    except Exception as e:
        print(f"⚠️ فشل الاتصال بـ Gemini: {e}", flush=True)

    print("⚠️ تفعيل الوضع الافتراضي", flush=True)
    return "dark cinematic rain", f"تلاوة خاشعة | سورة {surah_name} 🤍", f"#القرآن_الكريم #سورة_{surah_name}"

def clean_arabic(text):
    for s in ['۝', '۞', 'ۚ', 'ۖ', 'ۗ', 'ۘ', 'ۛ', 'ۜ']: text = text.replace(s, '')
    return text.strip()

def to_arabic_num(num):
    arabic_digits = {'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'}
    return "".join(arabic_digits.get(c, c) for c in str(num))

def get_font_base64():
    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        with open(font_path, "wb") as f: f.write(requests.get(QURAN_FONT_URL).content)
    with open(font_path, "rb") as f: return base64.b64encode(f.read()).decode("ascii")

def prepare_ai_background(bg_query, tag):
    raw_bg = f"raw_bg_{tag}.mp4"
    fast_bg = f"ready_bg_{tag}.mp4"
    
    print(f"🎬 المخرج (AI) طلب خلفية بنمط: '{bg_query}'... جاري البحث", flush=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    p_headers = {"Authorization": pexels_key} if pexels_key else {}
    success = False

    try:
        api_url = "https://" + "api.pexels.com" + f"/videos/search?query={bg_query}&orientation=portrait&per_page=10"
        r = requests.get(api_url, headers=p_headers, timeout=15).json()
        videos = r.get("videos", [])
        if videos:
            v = random.choice(videos)
            hd_file = sorted(v.get("video_files", []), key=lambda x: x.get("width", 0))[-1]
            with open(raw_bg, "wb") as f: f.write(requests.get(hd_file.get("link"), timeout=60).content)
            if os.path.getsize(raw_bg) > 100000:
                success = True
    except Exception:
        pass

    if not success:
        print("⚠️ فشل جلب فيديو من Pexels، جاري استخدام الخلفية الاحتياطية...", flush=True)
        fallback_url = "https://" + "assets.mixkit.co" + "/videos/preview/mixkit-stars-in-space-1610-large.mp4"
        try:
            with open(raw_bg, "wb") as f: f.write(requests.get(fallback_url, timeout=60).content)
            if os.path.getsize(raw_bg) > 100000:
                success = True
        except Exception:
            pass

    if not success:
        print("⚠️ توليد خلفية لونية برمجياً...", flush=True)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#080d14:s=1080x1920:d=60",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", fast_bg
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(raw_bg): os.remove(raw_bg)
        return fast_bg

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

    print("📥 سحب السورة كاملة...", flush=True)
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    surah_url = "https://" + "api.alquran.cloud" + f"/v1/surah/{surah_num}/{reciter_info['id']}"
    surah_data = None
    
    for attempt in range(3):
        try:
            req = requests.get(surah_url, headers=req_headers, timeout=20)
            if req.status_code == 200:
                surah_data = req.json().get("data", {}).get("ayahs", [])
                if surah_data:
                    break
        except Exception:
            time.sleep(2)
            
    if not surah_data:
        raise Exception("❌ لم يتم جلب بيانات السورة.")
    
    print("✂️ جاري قص وضبط تزامن الآيات...", flush=True)
    for a in range(start_a, end_a + 1):
        ayah_item = next((item for item in surah_data if item["numberInSurah"] == a), None)
        
        if not ayah_item:
            continue
            
        try:
            aud_file = f"aud_{a}_{tag}.mp3"
            global_ayah_num = ayah_item.get("number", 1)
            
            audio_sources = [
                ayah_item.get("audio"),
                ayah_item.get("audioSecondary"),
                "https://" + "cdn.islamic.network" + f"/quran/audio/128/{reciter_info['id']}/{global_ayah_num}.mp3",
                "https://" + "everyayah.com" + f"/data/{reciter_info['everyayah']}/{str(surah_num).zfill(3)}{str(a).zfill(3)}.mp3"
            ]
            
            audio_downloaded = False
            for src_url in audio_sources:
                if not src_url: continue
                try:
                    req_aud = requests.get(src_url, headers=req_headers, timeout=15)
                    if req_aud.status_code == 200 and len(req_aud.content) > 5000:
                        with open(aud_file, "wb") as f: 
                            f.write(req_aud.content)
                        audio_downloaded = True
                        break
                except Exception:
                    pass
                    
            if not audio_downloaded:
                raise Exception("فشل تحميل الصوت.")

            temp_files.append(aud_file)
            
            text = clean_arabic(ayah_item.get("text", ""))
            if a == 1 and surah_num != 1: 
                text = text.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "").replace("بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ", "").strip()
            
            a_clip = AudioFileClip(aud_file)
            mins, secs = int(current_time // 60), int(current_time % 60)
            
            frame_path = render_lower_verse_frame(f"{text} ﴿{to_arabic_num(a)}﴾", f"{mins:02d}:{secs:02d}", f"{a}_{tag}", font_b64)
            temp_files.append(frame_path)
            
            audio_clips.append(a_clip)
            video_clips.append(ImageClip(frame_path).set_duration(a_clip.duration))
            current_time += a_clip.duration
            
        except Exception as e:
            print(f"⚠️ خطأ في الآية {a}: {e}", flush=True)
            continue

    if not audio_clips:
        raise Exception("❌ لم يتم معالجة أي آية.")

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

def upload_files(video_file):
    print("☁️ جاري رفع الفيديو للحصول على رابط مباشر...", flush=True)
    try:
        with open(video_file, "rb") as f:
            up_url = "https://" + "catbox.moe" + "/user/api.php"
            r = requests.post(up_url, data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=120)
            if r.status_code == 200 and r.text.startswith("http"):
                link = r.text.strip()
                print(f"✅ تم الرفع بنجاح: {link}", flush=True)
                return link
    except Exception as e:
        print(f"⚠️ خطأ في الرفع: {e}", flush=True)
    return None

def post_to_buffer(video_url, text_content):
    token = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    channel_id = os.getenv("BUFFER_CHANNEL_ID", "").strip()
    
    if not token or not channel_id:
        print("⚠️ بيانات Buffer (Token أو Channel ID) غير متوفرة.", flush=True)
        return False
        
    print("📢 جاري النشر عبر Buffer...", flush=True)
    try:
        url = "https://" + "api.bufferapp.com" + "/1/updates/create.json"
        payload = {
            "access_token": token,
            "profile_ids[]": channel_id,
            "text": text_content,
            "media[video]": video_url
        }
        res = requests.post(url, data=payload, timeout=30)
        if res.status_code == 200 and res.json().get("success"):
            print("✅ تم النشر عبر Buffer بنجاح!", flush=True)
            return True
        else:
            print(f"⚠️ فشل النشر عبر Buffer: {res.text}", flush=True)
    except Exception as e:
        print(f"⚠️ خطأ في الاتصال بـ Buffer: {e}", flush=True)
    return False

def notify_telegram(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.getenv('ADMIN_CHAT_ID', '').strip()
    if not token or not chat_id:
        return
    try:
        tg_url = "https://" + "api.telegram.org" + f"/bot{token}/sendMessage"
        requests.post(tg_url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except:
        pass

if __name__ == "__main__":
    reciter = random.choice(RECITERS_POOL)
    
    meta_url = "https://" + "api.alquran.cloud" + "/v1/meta"
    surahs = requests.get(meta_url).json()["data"]["surahs"]["references"]
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
    
    # رفع الفيديو للحصول على رابط مباشر
    video_url = upload_files(vid_file)
    
    buffer_success = False
    if video_url:
        full_post_text = f"{yt_title}\n\n{caption}\n\n شاهد الفيديو: {video_url}"
        buffer_success = post_to_buffer(video_url, full_post_text)
    
    report = f"✨ <b>الذكاء الاصطناعي أتم المهمة بنجاح!</b>\n\n📖 <b>السورة:</b> {surah['name']} ({start_a}-{end_a})\n🎙️ <b>القارئ:</b> {reciter['name']}\n📝 <b>العنوان:</b> {yt_title}\n\n🔗 <b>رابط الفيديو:</b> <a href='{video_url}'>هنا</a>\n🚀 <b>حالة النشر عبر Buffer:</b> {'تم النشر بنجاح ✅' if buffer_success else 'فشل النشر ❌'}"
    notify_telegram(report)
    
    if os.path.exists(vid_file): os.remove(vid_file)
    print("🎉 تمت العملية بالكامل بنجاح!", flush=True)

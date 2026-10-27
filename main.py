import os
import sys
import json
import time
import uuid
import random
import shutil
import datetime
import subprocess
import requests

HISTORY_FILE = "history_parts.json"

RECITERS_POOL = [
    {"id": "Hudhaify_128kbps", "name": "علي الحذيفي"},
    {"id": "Abdullah_Basfar_192kbps", "name": "عبد الله بسفر"},
    {"id": "Abu_Bakr_Ash-Shaatree_128kbps", "name": "أبو بكر الشاطري"},
    {"id": "Muhammad_Ayyoub_128kbps", "name": "محمد أيوب"}
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active_surah": None, "next_ayah": 1, "part": 1, "completed_surahs": []}
    return {"active_surah": None, "next_ayah": 1, "part": 1, "completed_surahs": []}

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_surah_meta(surah_num):
    try:
        r = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}/en.asad", timeout=20).json()
        s_data = r.get("data", {})
        return {
            "number": s_data.get("number"),
            "name": s_data.get("name").replace("سُورَةُ ", "").strip(),
            "ayahs": s_data.get("numberOfAyahs")
        }
    except Exception:
        return {"number": 18, "name": "الكهف", "ayahs": 110}

def get_next_chunk(is_friday):
    history = load_history()
    if is_friday:
        s_meta = get_surah_meta(18)
        return {"surah": 18, "name": "الكهف", "start": 1, "total_ayahs": 110, "part": 1}
    
    if history.get("active_surah"):
        surah_num = history["active_surah"]
        current_ayah = history.get("next_ayah", 1)
        part_num = history.get("part", 1)
        s_meta = get_surah_meta(surah_num)
        return {
            "surah": surah_num,
            "name": s_meta["name"],
            "start": current_ayah,
            "total_ayahs": s_meta["ayahs"],
            "part": part_num
        }
    else:
        completed = set(history.get("completed_surahs", []))
        all_surahs = [i for i in range(1, 115) if i != 18 and i not in completed]
        if not all_surahs:
            all_surahs = [i for i in range(1, 115) if i != 18]
            history["completed_surahs"] = []
        surah_num = random.choice(all_surahs)
        s_meta = get_surah_meta(surah_num)
        return {
            "surah": surah_num,
            "name": s_meta["name"],
            "start": 1,
            "total_ayahs": s_meta["ayahs"],
            "part": 1
        }

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

def generate_landscape_cover(surah_name, part_num, ayah_range_text, reciter_name, out_cover):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ 
    width: 1920px; 
    height: 1080px; 
    background: radial-gradient(circle at center, #1b263b 0%, #0d1b2a 100%); 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    font-family: 'Amiri', serif;
  }}
  .box {{ 
    width: 1800px; 
    height: 960px; 
    border: 3px solid rgba(212, 175, 55, 0.45); 
    border-radius: 28px; 
    background: rgba(13, 27, 42, 0.75); 
    display: flex; 
    flex-direction: column; 
    justify-content: center; 
    align-items: center; 
    text-align: center; 
  }}
  .badge {{ 
    font-size: 36px; 
    color: #fff; 
    background: rgba(0,0,0,0.6); 
    padding: 12px 42px; 
    border-radius: 30px; 
    border: 1px solid rgba(212,175,55,0.4); 
    margin-bottom: 24px; 
  }}
  .title {{ 
    font-size: 110px; 
    font-weight: bold; 
    color: #D4AF37; 
    margin-bottom: 20px; 
    text-shadow: 0 0 30px rgba(212,175,55,0.8); 
  }}
  .part {{ font-size: 52px; color: #ffffff; margin-bottom: 20px; }}
  .reciter {{ font-size: 44px; color: #e0e1dd; margin-bottom: 20px; }}
  .sub {{ font-size: 32px; color: rgba(212,175,55,0.95); }}
</style></head>
<body><div class="box">
  <div class="badge">🕌 تلاوة مباركة خاشعة 🌿</div>
  <div class="title">سُورَةُ {surah_name}</div>
  <div class="part">الجزء {part_num} • {ayah_range_text}</div>
  <div class="reciter">بصوت القارئ الشيخ / {reciter_name}</div>
  <div class="sub">تلاوة هادئة بجودة صوت نقية عالية HD</div>
</div></body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([
        chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", 
        "--window-size=1920,1080", f"--screenshot={os.path.abspath(out_cover)}", 
        f"file://{os.path.abspath(h_path)}"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): 
        os.remove(h_path)
    return out_cover

def download_chunk_audio(surah_num, start_a, total_ayahs, rec_id, tag):
    downloaded_files = []
    tmp_list = f"list_{tag}.txt"
    s_str = f"{surah_num:03d}"
    curr_duration = 0.0
    end_a = start_a

    print(f"📥 جاري تجميع مقطع لا يتجاوز 8 دقائق بدءاً من الآية {start_a}...", flush=True)

    with open(tmp_list, "w", encoding="utf-8") as lf:
        for a in range(start_a, total_ayahs + 1):
            a_str = f"{a:03d}"
            part_file = f"p_{tag}_{s_str}_{a_str}.mp3"
            url = f"https://everyayah.com/data/{rec_id}/{s_str}{a_str}.mp3"

            for _ in range(3):
                try:
                    r = requests.get(url, timeout=25)
                    if r.status_code == 200 and len(r.content) > 1000:
                        with open(part_file, "wb") as pf:
                            pf.write(r.content)
                        break
                except Exception:
                    time.sleep(1)

            if not os.path.exists(part_file):
                break

            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", part_file]
            try:
                dur = float(subprocess.check_output(probe_cmd).strip())
            except Exception:
                dur = 5.0

            if curr_duration + dur > 460.0 and a > start_a:
                if os.path.exists(part_file): 
                    os.remove(part_file)
                break

            lf.write(f"file '{os.path.abspath(part_file)}'\n")
            downloaded_files.append(part_file)
            curr_duration += dur
            end_a = a

    raw_audio = f"raw_{tag}.mp3"
    final_audio = f"aud_final_{tag}.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", tmp_list, "-c", "copy", raw_audio], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_audio,
        "-filter_complex", "[0:a]asetrate=44100*1.040,atempo=0.961,volume=1.12[aout]",
        "-map", "[aout]", "-b:a", "192k", "-ar", "44100", final_audio
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(tmp_list): 
        os.remove(tmp_list)
    if os.path.exists(raw_audio): 
        os.remove(raw_audio)
    for f in downloaded_files:
        if os.path.exists(f): 
            os.remove(f)

    return final_audio, end_a, curr_duration

def build_part_video(chunk_info, reciter_info, tag):
    rec_id = reciter_info["id"]
    rec_name = reciter_info["name"]

    final_audio, end_a, duration = download_chunk_audio(
        chunk_info["surah"], chunk_info["start"], chunk_info["total_ayahs"], rec_id, tag
    )

    ayah_range_text = f"الآيات ({chunk_info['start']} - {end_a})"
    cover_file = f"cover_{tag}.jpg"
    generate_landscape_cover(chunk_info["name"], chunk_info["part"], ayah_range_text, rec_name, cover_file)

    out_video = f"final_{tag}.mp4"
    print(f"🎬 إنشاء فيديو الجزء {chunk_info['part']} بمدة {int(duration)} ثانية...", flush=True)

    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", cover_file, "-i", final_audio,
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", out_video
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(final_audio): 
        os.remove(final_audio)
    return out_video, cover_file, end_a, rec_name

def upload_files(video_file):
    print("📤 جاري رفع ملف الفيديو...", flush=True)
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if repo and gh_token:
        tag_name = f"rel-{int(time.time()*1000)}"
        try:
            res = requests.post(
                f"https://api.github.com/repos/{repo}/releases",
                headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
                json={"tag_name": tag_name, "name": f"Surah {tag_name}", "draft": False}, timeout=30
            ).json()
            if "upload_url" in res:
                u_url = res["upload_url"].split("{")[0]
                with open(video_file, "rb") as vf:
                    up_res = requests.post(f"{u_url}?name=video.mp4", headers={"Authorization": f"token {gh_token}", "Content-Type": "video/mp4"}, data=vf, timeout=180).json()
                browser_url = up_res.get("browser_download_url")
                if browser_url:
                    print(f"✅ تم الرفع كـ Release على GitHub: {browser_url}", flush=True)
                    return browser_url
        except Exception as e:
            print(f"⚠️ خطأ في GitHub Releases: {e}", flush=True)

    try:
        with open(video_file, "rb") as f:
            r = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=180)
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
                print(f"✅ نجح إرسال المنشور لـ Buffer للقناة {ch_id} (Post ID: {post_data['post'].get('id')})", flush=True)
            else:
                print(f"❌ رد Buffer للقناة {ch_id}: {post_data.get('message', res)}", flush=True)
        except Exception as e:
            print(f"❌ خطأ أثناء الاتصال بـ Buffer: {e}", flush=True)

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

    chunk_info = get_next_chunk(is_friday)
    tag = f"quran_{chunk_info['surah']}_p{chunk_info['part']}_{int(time.time())}"

    print(f"🎬 تجهيز سورة {chunk_info['name']} (الجزء {chunk_info['part']}) من الآية {chunk_info['start']}...", flush=True)

    vid_file, cov_file, end_ayah, r_name = build_part_video(chunk_info, reciter, tag)

    yt_title = f"سورة {chunk_info['name']} (الجزء {chunk_info['part']}) الآيات ({chunk_info['start']}-{end_ayah}) | القارئ {r_name} 🤍"
    caption = (
        f"📖 سورة {chunk_info['name']} - الجزء {chunk_info['part']}\n"
        f"🎙️ بصوت القارئ الشيخ: {r_name}\n"
        f"✨ الآيات الكريمة: من الآية ({chunk_info['start']}) إلى ({end_ayah})\n\n"
        f"اللهم اجعل القرآن الكريم ربيع قلوبنا ونور صدورنا وجلاء أحزاننا 🤍\n\n"
        f"#سورة_{chunk_info['name']} #القرآن_الكريم #تلاوة_خاشعة #راحة_نفسية"
    )

    pub_url = upload_files(vid_file)
    if pub_url:
        post_to_buffer(pub_url, yt_title, caption)
    else:
        print("❌ فشل الحصول على رابط تحميل للفيديو، لم يتم الإرسال لـ Buffer.", flush=True)

    if not is_friday:
        hist = load_history()
        if end_ayah >= chunk_info["total_ayahs"]:
            hist["active_surah"] = None
            hist["next_ayah"] = 1
            hist["part"] = 1
            if chunk_info["surah"] not in hist.get("completed_surahs", []):
                hist["completed_surahs"].append(chunk_info["surah"])
            print(f"🎉 تم الانتهاء من نشر سورة {chunk_info['name']} كاملة!", flush=True)
        else:
            hist["active_surah"] = chunk_info["surah"]
            hist["next_ayah"] = end_ayah + 1
            hist["part"] = chunk_info["part"] + 1
            print(f"📌 تم حفظ التقدم: الجزء القادم سيبدأ من الآية {end_ayah + 1}", flush=True)
        save_history(hist)

    report = (
        f"✨ <b>تم إنتاج ونشر جزء جديد مدته أقل من 8 دقائق!</b>\n\n"
        f"📖 <b>السورة:</b> سورة {chunk_info['name']} (الجزء {chunk_info['part']})\n"
        f"🔢 <b>الآيات:</b> ({chunk_info['start']} إلى {end_ayah})\n"
        f"🎙️ <b>القارئ:</b> {r_name}\n"
        f"🖥️ <b>الأبعاد:</b> 1920x1080 (أفقي كامل)\n"
        f"🔗 <b>الرابط:</b> <a href='{pub_url}'>مشاهدة المقطع</a>"
    )
    notify_telegram(report, cov_file)

    if os.path.exists(vid_file): 
        os.remove(vid_file)
    if os.path.exists(cov_file): 
        os.remove(cov_file)
    print("=== اكتمل الرندر، التحديث، والنشر بنجاح ===", flush=True)

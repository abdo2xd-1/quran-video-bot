import os
import sys
import json
import time
import random
import datetime
import subprocess
import requests

from moviepy.editor import (
    VideoFileClip, AudioFileClip, 
    CompositeVideoClip, concatenate_audioclips
)

HISTORY_FILE = "history_shorts_all.json"

# الرابط المباشر لمشهد الشارع المبلل والترام تحت المطر بفرنسا
EXACT_BORDEAUX_RAIN_VIDEO = "https://assets.mixkit.co/videos/preview/mixkit-walking-down-a-wet-street-with-tram-tracks-in-bordeaux-41315-large.mp4"

# الشيوخ المحددين فقط (مع معرفات everyayah لضمان قص الآيات بشكل دقيق 100%)
RECITERS_POOL = [
    {"name": "محمد صديق المنشاوي", "everyayah": "Minshawy_Murattal_128kbps"},
    {"name": "ياسر الدوسري", "everyayah": "Yasser_Ad-Dussary_128kbps"}
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

def build_audio_for_ayahs(surah_num, start_a, end_a, reciter_info, tag):
    """تحميل كل آية بشكل منفصل ودمجها لضمان توافق الصوت مع النهاية بالثانية بالضبط"""
    clips = []
    temp_files = []
    print(f"📥 جاري تحميل ودمج الآيات من {start_a} إلى {end_a} بدقة متناهية...", flush=True)
    
    for a in range(start_a, end_a + 1):
        s_str = str(surah_num).zfill(3)
        a_str = str(a).zfill(3)
        url = f"https://everyayah.com/data/{reciter_info['everyayah']}/{s_str}{a_str}.mp3"
        file_name = f"aud_{tag}_{s_str}_{a_str}.mp3"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(file_name, "wb") as f:
                    f.write(r.content)
                clips.append(AudioFileClip(file_name))
                temp_files.append(file_name)
        except Exception as e:
            print(f"⚠️ خطأ في تحميل الآية {a}: {e}", flush=True)
            
    if not clips:
        raise Exception("❌ فشل تحميل الآيات، قد يكون هناك مشكلة في الاتصال بالخادم.")
        
    final_aud = concatenate_audioclips(clips)
    aud_file = f"final_aud_{tag}.mp3"
    final_aud.write_audiofile(aud_file, logger=None)
    
    for f in temp_files:
        if os.path.exists(f): 
            try: os.remove(f)
            except: pass
            
    return aud_file, final_aud.duration

def prepare_exact_bordeaux_video(tag):
    raw_bg = f"raw_bordeaux_{tag}.mp4"
    fast_bg = f"ready_bordeaux_{tag}.mp4"

    print("🎥 محاولة جلب فيديو Mixkit الأصلي للمطر...", flush=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    success = False

    try:
        res = requests.get(EXACT_BORDEAUX_RAIN_VIDEO, headers=headers, timeout=20)
        res.raise_for_status()
        with open(raw_bg, "wb") as f:
            f.write(res.content)
        if os.path.getsize(raw_bg) > 100000:
            success = True
    except Exception as e:
        print(f"⚠️ تم حظر Mixkit (403)، جاري التحويل للملاذ الآمن... ({e})", flush=True)

    if not success:
        print("🔄 جلب مشهد مطر بديل باستخدام مفتاح Pexels API المعتمد...", flush=True)
        pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
        p_headers = {"Authorization": pexels_key} if pexels_key else {}
        
        try:
            api_url = "https://api.pexels.com/videos/search?query=rain+street+dark+moody&orientation=portrait&per_page=15"
            r = requests.get(api_url, headers=p_headers, timeout=15).json()
            videos = r.get("videos", [])
            
            if videos:
                v = random.choice(videos)
                hd_file = sorted(v.get("video_files", []), key=lambda x: x.get("width", 0))[-1]
                res2 = requests.get(hd_file.get("link"), timeout=60)
                res2.raise_for_status()
                with open(raw_bg, "wb") as f:
                    f.write(res2.content)
            else:
                print("❌ لم يتم العثور على نتائج في Pexels.", flush=True)
        except Exception as e2:
            print(f"❌ فشل الاتصال بـ Pexels API أيضاً: {e2}", flush=True)

    if not os.path.exists(raw_bg) or os.path.getsize(raw_bg) < 100000:
        print("⚠️ إنشاء خلفية سينمائية مظلمة مؤقتة لتفادي انهيار النظام...", flush=True)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#080d14:s=1080x1920:d=60",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", fast_bg
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(raw_bg): os.remove(raw_bg)
        return fast_bg

    scale_cmd = [
        "ffmpeg", "-y", "-i", raw_bg,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-b:v", "6000k", "-an", fast_bg
    ]
    subprocess.run(scale_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(raw_bg): 
        os.remove(raw_bg)
    return fast_bg

def build_fast_short_video(surah_num, surah_name, start_a, end_a, reciter_info, tag):
    rec_name = reciter_info["name"]

    # 1. بناء الصوت المدمج للآيات والحصول على الطول الدقيق
    aud_file, tot_dur = build_audio_for_ayahs(surah_num, start_a, end_a, reciter_info, tag)
    audio_clip = AudioFileClip(aud_file)

    # 2. بناء الخلفية ومطابقة طولها لطول الصوت بالظبط (سينتهي الفيديو مع الآية)
    fast_bg = prepare_exact_bordeaux_video(tag)
    bg = VideoFileClip(fast_bg)
    bg = bg.loop(duration=tot_dur) if bg.duration < tot_dur else bg.subclip(0, tot_dur)
    
    # 3. دمج الصوت مع الصورة (بدون أي نصوص)
    main_video = bg.set_audio(audio_clip).set_duration(tot_dur)

    out_file = f"final_{tag}.mp4"
    main_video.write_videofile(
        out_file, fps=30, codec="libx264", audio_codec="aac", 
        bitrate="6000k", threads=4, preset="medium"
    )

    if os.path.exists(aud_file): os.remove(aud_file)
    if os.path.exists(fast_bg): os.remove(fast_bg)

    return out_file, rec_name

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
        return False
    channel_ids = [c.strip() for c in channels_raw.split(",") if c.strip()]
    graphql_url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {buffer_token}", "Content-Type": "application/json"}
    mutation = """mutation CreatePost($input: CreatePostInput!) { 
        createPost(input: $input) { 
            ... on PostActionSuccess { post { id status } } 
            ... on MutationError { message } 
        } 
    }"""
    
    success = False
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
                print(f"✅ نجح إرسال Shorts لـ Buffer للقناة {ch_id}", flush=True)
                success = True
            else:
                print(f"❌ رد Buffer للقناة {ch_id}: {post_data.get('message', res)}", flush=True)
        except Exception as e:
            print(f"❌ خطأ أثناء الاتصال بـ Buffer: {e}", flush=True)
            
    return success

def post_to_dailymotion(video_file, title, description, tags="quran,islam,shorts"):
    api_key = os.getenv("DAILYMOTION_KEY", "").strip()
    api_secret = os.getenv("DAILYMOTION_SECRET", "").strip()
    username = os.getenv("DAILYMOTION_USERNAME", "").strip()
    password = os.getenv("DAILYMOTION_PASSWORD", "").strip()

    if not all([api_key, api_secret, username, password]):
        return None

    try:
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
        if not access_token: return None
        headers = {"Authorization": f"Bearer {access_token}"}

        upload_url_res = requests.get("https://api.dailymotion.com/file/upload", headers=headers, timeout=20).json()
        upload_url = upload_url_res.get("upload_url")

        with open(video_file, "rb") as f:
            up_res = requests.post(upload_url, files={"file": f}, timeout=180).json()
        file_url = up_res.get("url")

        if not file_url: return None

        publish_data = {
            "url": file_url, "title": title[:250], "description": description,
            "tags": tags, "channel": "lifestyle", "published": "true", "is_created_for_kids": "false"
        }
        create_res = requests.post("https://api.dailymotion.com/me/videos", headers=headers, data=publish_data, timeout=30).json()

        video_id = create_res.get("id")
        if video_id:
            dm_link = f"https://www.dailymotion.com/video/{video_id}"
            print(f"✅ تم نشر الفيديو بنجاح على Dailymotion: {dm_link}", flush=True)
            return dm_link
    except Exception as e:
        pass
    return None

def post_to_odysee(video_file, title, description, tags=None):
    if tags is None: tags = ["quran", "islam", "shorts", "reels"]
    auth_token = os.getenv("ODYSEE_AUTH_TOKEN", "").strip()
    if not auth_token or not os.path.exists(video_file): return None

    try:
        headers = {"Content-Type": "application/json-rpc", "X-Lbry-Auth-Token": auth_token}
        channel_id = "d2a1e5238cbfc0b0a210a7f7d1d815c5f075d9a4"
        file_size = os.path.getsize(video_file)
        file_name = os.path.basename(video_file)
        clean_stream_name = f"quran-short-{int(time.time())}"

        meta_fn = base64.b64encode(file_name.encode()).decode()
        meta_tk = base64.b64encode(auth_token.encode()).decode()

        upload_servers = ["https://upload.lbry.com/upload", "https://api.odysee.com/upload"]
        upload_location = None
        for srv in upload_servers:
            try:
                init_res = requests.post(
                    srv, headers={"Tus-Resumable": "1.0.0", "Upload-Length": str(file_size), "Upload-Metadata": f"filename {meta_fn},auth_token {meta_tk}"}, timeout=15
                )
                loc = init_res.headers.get("Location")
                if loc:
                    if loc.startswith("/"):
                        from urllib.parse import urlparse
                        p = urlparse(srv)
                        loc = f"{p.scheme}://{p.netloc}{loc}"
                    upload_location = loc
                    break
            except Exception: continue

        if not upload_location: return None

        with open(video_file, "rb") as vf:
            patch_res = requests.patch(
                upload_location, headers={"Tus-Resumable": "1.0.0", "Upload-Offset": "0", "Content-Type": "application/offset+octet-stream"}, data=vf, timeout=300
            )

        if patch_res.status_code not in [200, 204]: return None
        file_id = upload_location.rstrip("/").split("/")[-1]

        publish_params = {
            "name": clean_stream_name, "title": title[:95], "description": description,
            "tags": tags, "languages": ["ar"], "bid": "0.0001", "file_path": file_id, "channel_id": channel_id
        }
        payload = {"jsonrpc": "2.0", "method": "publish", "params": publish_params, "id": int(time.time())}
        pub_res = requests.post("https://api.na-backend.odysee.com/api/v1/proxy?m=publish", headers=headers, json=payload, timeout=60).json()

        claim_info = pub_res.get("result", {}).get("outputs", [{}])[0]
        claim_name = claim_info.get("name")
        res_claim_id = claim_info.get("claim_id")

        if claim_name and res_claim_id:
            odysee_url = f"https://odysee.com/{claim_name}:{res_claim_id}"
            print(f"✅ تم النشر بنجاح على Odysee: {odysee_url}", flush=True)
            return odysee_url
    except Exception:
        pass
    return None

def notify_telegram(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not bot_token or not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
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

    # 5 آيات كحد أدنى كما طلبت
    chunk_size = 5
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
        
        # 5 آيات كحد أدنى كما طلبت
        chunk_size = 5 if total_ayahs >= 5 else total_ayahs
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
                "key": clip_key
            }

    history["posted_keys"] = []
    s = random.choice([x for x in surahs if x["ayahs"] >= 5 and x["number"] != 18])
    return {"surah": s["number"], "name": s["name"], "start": 1, "end": 5, "part": None, "key": f"{s['number']}_1_5_{int(time.time())}"}

if __name__ == "__main__":
    local_egypt_time = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    is_friday = (local_egypt_time.weekday() == 4)
    reciter = random.choice(RECITERS_POOL)
    history = load_history()

    if is_friday:
        week_str = local_egypt_time.strftime("%Y_%U")
        item = get_friday_kahf_chunk(history, week_str)
        print(f"🌟 الجمعة المبارك: إنتاج سورة الكهف - الآيات ({item['start']}-{item['end']})...", flush=True)
        # اسم السورة فقط في العنوان كما طلبت
        yt_title = f"سورة الكهف #shorts"
        caption = (
            f"📖 سورة الكهف\n"
            f"✨ الآيات الكريمة: ({item['start']} - {item['end']})\n"
            f"🎙️ بصوت القارئ: {reciter['name']}\n\n"
            f"تلاوة خاشعة تريح القلوب من سورة الكهف المباركة ليوم الجمعة 🤍\n\n"
            f"{SEO_HASHTAGS} #يوم_الجمعة #سورة_الكهف"
        )
    else:
        item = pick_unposted_clip_all_quran(history)
        print(f"🎬 المقطع العشوائي: سورة {item['name']} الآيات ({item['start']}-{item['end']})...", flush=True)
        # اسم السورة فقط في العنوان كما طلبت
        yt_title = f"سورة {item['name']} #shorts"
        caption = (
            f"📖 سورة {item['name']} | الآيات ({item['start']} - {item['end']})\n"
            f"🎙️ بصوت القارئ: {reciter['name']}\n\n"
            f"اللهم اجعل القرآن ربيع قلوبنا ونور صدورنا وجلاء أحزاننا 🤍\n\n"
            f"{SEO_HASHTAGS} #سورة_{item['name']} #تلاوة_خاشعة"
        )

    tag = f"short_{item['key']}_{int(time.time())}"

    vid_file, r_name = build_fast_short_video(
        item["surah"], item["name"], item["start"], item["end"], reciter, tag
    )

    pub_url = upload_files(vid_file)

    buffer_success = False
    if pub_url:
        full_post_text = f"{yt_title}\n\n{caption}\n\n شاهد المقطع: {pub_url}"
        buffer_success = post_to_buffer(pub_url, yt_title, full_post_text)
    else:
        print("❌ فشل الحصول على رابط، تم تخطي Buffer.", flush=True)

    dm_link = post_to_dailymotion(vid_file, yt_title, caption, tags=SEO_TAGS_YOUTUBE)
    odysee_link = post_to_odysee(vid_file, yt_title, caption, tags=SEO_TAGS_YOUTUBE.split(", "))

    if not is_friday:
        if item["key"] not in history["posted_keys"]:
            history["posted_keys"].append(item["key"])

    save_history(history)

    dm_report = f"\n📺 <b>Dailymotion:</b> <a href='{dm_link}'>مشاهدة المقطع</a>" if dm_link else ""
    odysee_report = f"\n🎥 <b>Odysee:</b> <a href='{odysee_link}'>مشاهدة المقطع</a>" if odysee_link else ""
    report = (
        f"✨ <b>تم إنتاج ونشر المقطع بنجاح! (بدون نصوص)</b>\n\n"
        f"📖 <b>السورة:</b> {item['name']}\n"
        f"🔢 <b>الآيات:</b> ({item['start']} إلى {item['end']})\n"
        f"🎙️ <b>القارئ:</b> {r_name}\n"
        f"🚀 <b>حالة Buffer:</b> {'نجاح ✅' if buffer_success else 'فشل ❌'}\n"
        f"🔗 <b>رابط التحميل:</b> <a href='{pub_url}'>هنا</a>"
        f"{dm_report}"
        f"{odysee_report}"
    )
    notify_telegram(report)

    if os.path.exists(vid_file): os.remove(vid_file)
    print("=== اكتمل الرندر للشورتس، التحديث، والنشر بنجاح ===", flush=True)

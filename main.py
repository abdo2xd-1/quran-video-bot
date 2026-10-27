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

HISTORY_FILE = "history_parts.json"
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Bold.ttf"

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
        r = requests.get(f"https://api.alquran.cloud/v1/surah/{surah_num}/en.asad", timeout=15).json()
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
        # يوم الجمعة سورة الكهف دائماً
        s_meta = get_surah_meta(18)
        current_ayah = 1
        part_num = 1
        surah_num = 18
        surah_name = "الكهف"
        total_ayahs = 110
    else:
        # باقي الأيام: إكمال السورة الحالية أو اختيار سورة جديدة عشوائية
        if history.get("active_surah"):
            surah_num = history["active_surah"]
            current_ayah = history.get("next_ayah", 1)
            part_num = history.get("part", 1)
            s_meta = get_surah_meta(surah_num)
            surah_name = s_meta["name"]
            total_ayahs = s_meta["ayahs"]
        else:
            completed = set(history.get("completed_surahs", []))
            all_surahs = [i for i in range(1, 115) if i != 18 and i not in completed]
            if not all_surahs:
                all_surahs = [i for i in range(1, 115) if i != 18]
                history["completed_surahs"] = []
            surah_num = random.choice(all_surahs)
            s_meta = get_surah_meta(surah_num)
            surah_name = s_meta["name"]
            total_ayahs = s_meta["ayahs"]
            current_ayah = 1
            part_num = 1

    return {
        "surah": surah_num,
        "name": surah_name,
        "start": current_ayah,
        "total_ayahs": total_ayahs,
        "part": part_num
    }

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

def get_chrome():
    return shutil.which("google-chrome") or shutil.which("chromium-browser") or "google-chrome"

def generate_landscape_cover(surah_name, part_num, ayah_range_text, reciter_name, font_b64, out_cover):
    chrome_bin = get_chrome()
    html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: 'Amiri'; src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype'); }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ 
    width: 1920px; 
    height: 1080px; 
    background: radial-gradient(circle at center, #1b263b 0%, #0d1b2a 100%); 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    position: relative; 
    font-family: 'Amiri';
  }}
  .box {{ 
    width: 1800px; 
    height: 960px; 
    border: 3px solid rgba(212, 175, 55, 0.45); 
    border-radius: 28px;
    background: rgba(13, 27, 42, 0.65);
    display: flex; 
    flex-direction: column; 
    justify-content: center; 
    align-items: center; 
    text-align: center; 
  }}
  .badge {{ 
    font-size: 34px; 
    color: #fff; 
    background: rgba(0,0,0,0.6); 
    padding: 12px 40px; 
    border-radius: 30px; 
    border: 1px solid rgba(212,175,55,0.4); 
    margin-bottom: 24px; 
  }}
  .title {{ 
    font-size: 105px; 
    font-weight: bold; 
    color: #D4AF37; 
    margin-bottom: 20px; 
    text-shadow: 0 0 30px rgba(212,175,55,0.8); 
  }}
  .part {{
    font-size: 50px;
    color: #ffffff;
    margin-bottom: 20px;
  }}
  .reciter {{ 
    font-size: 42px; 
    color: #e0e1dd; 
    margin-bottom: 18px; 
  }}
  .sub {{ 
    font-size: 30px; 
    color: rgba(212,175,55,0.95); 
  }}
</style></head>
<body><div class="box">
  <div class="badge">🕌 تلاوة مباركة خاشعة 🌿</div>
  <div class="title">سُورَةُ {surah_name}</div>
  <div class="part">الجزء {part_num} • {ayah_range_text}</div>
  <div class="reciter">بصوت القارئ الشيخ / {reciter_name}</div>
  <div class="sub">تلاوة هادئة بجودة صوت نقية HD</div>
</div></body></html>"""

    h_path = "tmp_cov.html"
    with open(h_path, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([
        chrome_bin, "--headless", "--no-sandbox", "--disable-gpu", 
        "--window-size=1920,1080", f"--screenshot={os.path.abspath(out_cover)}", 
        f"file://{os.path.abspath(h_path)}"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(h_path): os.remove(h_path)
    return out_cover

def download_chunk_audio(surah_num, start_a, total_ayahs, rec_id, tag):
    """تحميل الآيات بالتتابع حتى الوصول إلى مدة 7.5 - 8 دقائق كحد أقصى"""
    downloaded_files = []
    tmp_list = f"list_{tag}.txt"
    s_str = f"{surah_num:03d}"
    curr_duration = 0.0
    end_a = start_a

    print(f"📥 جاري تجميع مقطع لا يتجاوز 8 دقائق ابتداءً من الآية {start_a}...", flush=True)

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

            # فحص مدة المقطع الحالي عبر ffprobe
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", part_file]
            try:
                dur = float(subprocess.check_output(probe_cmd).strip())
            except Exception:
                dur = 5.0

            # إذا كانت الإضافة ستتجاوز 7.8 دقيقة (470 ثانية) نتوقف عند هذه الآية
            if curr_duration + dur > 470.0 and a > start_a:
                if os.path.exists(part_file): os.remove(part_file)
                break

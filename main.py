import os
import sys
import random
import asyncio
import io
import re
import json
import urllib.parse
import requests
import numpy as np

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    setattr(PIL.Image, 'ANTIALIAS', PIL.Image.Resampling.LANCZOS)

from PIL import Image, ImageDraw, ImageFont, features
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    ColorClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    vfx
)

# ==============================================================================
# 1. المفاتيح والقنوات والهويات الوثائقية
# ==============================================================================
BUFFER_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

DEFAULT_CHANNELS = [
    "6abacd06ea19ca0bde180ef9", # أبعاد جغرافية
    "6abace11ea19ca0bde181821", # مشاريع عملاقة
    "6abace7bea19ca0bde181dff"  # مسار
]

env_channel_str = os.getenv("BUFFER_CHANNEL_IDS", "").strip()
if env_channel_str:
    raw_channels = [ch.strip() for ch in env_channel_str.replace("\n", ",").split(",") if ch.strip()]
    CHANNELS_LIST = list(dict.fromkeys(raw_channels))
else:
    CHANNELS_LIST = DEFAULT_CHANNELS

NICHE_PROFILES = {
    "أبعاد جغرافية": {
        "voice": "ar-EG-ShakirNeural",
        "rate": "+20%",
        "badge": "أبعاد جغرافية | أسرار الكوكب",
        "handle": "@AbaadGeo"
    },
    "مشاريع عملاقة": {
        "voice": "ar-EG-ShakirNeural",
        "rate": "+18%",
        "badge": "مشاريع عملاقة | معجزات هندسية",
        "handle": "@MegaProjects"
    },
    "مسار": {
        "voice": "ar-EG-ShakirNeural",
        "rate": "+18%",
        "badge": "مسار | أسرار التجارة العالمية",
        "handle": "@MasarFlow"
    }
}

NICHE_NAMES = list(NICHE_PROFILES.keys())
HISTORY_FILE = "published_history.json"

# ==============================================================================
# 2. حزمة المؤثرات والموسيقى وأصوات البيئة (Foley Suite)
# ==============================================================================
BGM_TRACKS = [
    "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=dark-mystery-trailer-111586.mp3",
    "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8bbf72242.mp3?filename=suspense-cinematic-ambient-109012.mp3"
]
SFX_WHOOSH_URL = "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c3527e30ec.mp3?filename=whoosh-6316.mp3"
SFX_IMPACT_URL = "https://cdn.pixabay.com/download/audio/2021/08/04/audio_12b0c7443c.mp3?filename=cinematic-boom-impact-114457.mp3"
SFX_POP_URL = "https://cdn.pixabay.com/download/audio/2022/03/24/audio_c29f6004b9.mp3?filename=pop-39222.mp3"
SFX_TYPING_URL = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_1d45124ec6.mp3?filename=keyboard-typing-5997.mp3"
SFX_RISER_URL = "https://cdn.pixabay.com/download/audio/2022/01/18/audio_24e93fb232.mp3?filename=tension-riser-6848.mp3"

FOLEY_OCEAN_URL = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_73236e84dc.mp3?filename=ocean-waves-112906.mp3"
FOLEY_WIND_URL = "https://cdn.pixabay.com/download/audio/2021/08/09/audio_1416bfb339.mp3?filename=wind-blowing-sfx-12809.mp3"
FOLEY_MACHINERY_URL = "https://cdn.pixabay.com/download/audio/2022/01/18/audio_82c23bc42a.mp3?filename=deep-rumble-6847.mp3"

def ensure_audio_assets():
    assets = {
        "sfx_whoosh.mp3": SFX_WHOOSH_URL,
        "sfx_impact.mp3": SFX_IMPACT_URL,
        "sfx_pop.mp3": SFX_POP_URL,
        "sfx_typing.mp3": SFX_TYPING_URL,
        "sfx_riser.mp3": SFX_RISER_URL,
        "foley_ocean.mp3": FOLEY_OCEAN_URL,
        "foley_wind.mp3": FOLEY_WIND_URL,
        "foley_machinery.mp3": FOLEY_MACHINERY_URL,
        "bgm_track.mp3": random.choice(BGM_TRACKS)
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    for filename, url in assets.items():
        if not os.path.exists(filename):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(r.content)
            except Exception as e:
                print(f"⚠️ تعذر تنزيل {filename}: {e}")

# ==============================================================================
# 3. سجل المواضيع واختبار الـ A/B Testing
# ==============================================================================
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(niche, title, strategy):
    hist = load_history()
    if niche not in hist:
        hist[niche] = []
    hist[niche].append({"title": title, "strategy": strategy})
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ==============================================================================
# 4. محرك الـ High-CPM والـ A/B Testing بالذكاء الاصطناعي
# ==============================================================================
FALLBACK_TOPICS_POOL = {
    "أبعاد جغرافية": [
        {
            "title_a": "[لغز غامض] بحيرة سرية في إفريقيا تحول الطيور لحجارة فوراً !! 😱⚡",
            "title_b": "[صدمة 60°] مياه قلوية كاوية تدمر كل من يقترب منها في دقائق !! ⚠️🔥",
            "desc": "أغرب ظاهرة على وجه الأرض ترتبط بأمن الموارد وسلاسل التوريد البيئية النادرة!\n\n🔴 تابع الوثائقي الكامل في قناتنا: https://youtube.com/@AbaadGeo\n#أبعاد_جغرافية #غرائب #حقائق_مرعبة #اقتصاد_المناخ #Shorts",
            "pinned_comment": "💬 لو عُرض عليك مليون دولار لتعيش هناك أسبوعاً كاملاً بمفردك.. توافق أم ترفض؟ اكتب رأيك بالتعليقات!",
            "scenes": [
                {"hook": "تخيل إن في بحيرة سرية في إفريقيا، أي طائر يلمس ميتها بيتحول لحجر فوراً!", "part1": "بحيرة النطرون", "part2": "بتحول الكائنات لحجر!", "coords": "02°25'S 36°00'E", "location_tag": "تنزانيا - إفريقيا", "query": "red lake volcanic thermal", "has_callout": True, "has_map_highlight": True},
                {"hook": "الموضوع مش سحر، حرارة المية بتوصل لستين درجة ومليانة أملاح كاوية بتحجر الأجسام!", "part1": "حرارة 60 مئوية", "part2": "أملاح قلوية كاوية!", "coords": "02°25'S 36°00'E", "location_tag": "الوادي المتصدع", "query": "boiling water volcanic thermal"},
                {"hook": "وفي أبرد قرية بروسيا، الحرارة بتنزل لواحد وسبعين تحت الصفر والأنفاس بتتجمد بثانية!", "part1": "برودة -71 مئوية", "part2": "الرموش تتجمد بثانية!", "coords": "63°27'N 142°47'E", "location_tag": "أويمياكون - روسيا", "query": "frozen siberia blizzard snow", "has_map_highlight": True},
                {"hook": "وحفرة بوابة جهنم في آسيا، مشتعلة بنيران غازية مستمرة وما انطفتش من خمسين سنة!", "part1": "بوابة جهنم", "part2": "مشتعلة من 50 سنة!", "coords": "40°15'N 58°26'E", "location_tag": "صحراء قره قوم", "query": "fire pit flames desert dark", "has_scale": True},
                {"hook": "لو اتعرض عليك مليون دولار لتعيش هناك أسبوع.. توافق؟ لأن سر الرعب ده بدأ مع...", "part1": "مليون $ للمغامرة؟", "part2": "اكتب رأيك الآن!", "coords": "GLOBAL RADAR", "location_tag": "كوكب الأرض", "query": "space earth cinematic night"}
            ]
        }
    ],
    "مشاريع عملاقة": [
        {
            "title_a": "[وحش ميكانيكي] أضخم آلة صنعتها البشرية حفرت تحت قاع البحر !! 🏗️😱",
            "title_b": "[استثمار بالمليارات] آلة حفر أنفاق تزن 7000 طن غيرت بنية التجارة العالمية !! 💰🏗️",
            "desc": "استثمارات البنية التحتية العملاقة وسلاسل الإمداد العالمية التي تحرك اقتصاد الدول الكبرى!\n\n🔴 شاهد قائمة المشاريع السيادية كاملة في قناتنا: https://youtube.com/@MegaProjects\n#مشاريع_عملاقة #هندسة #استثمارات_المليارات #بنية_تحتية #Shorts",
            "pinned_comment": "💬 هل ترى أن ضخ تريليونات الدولارات في هذه المشاريع العملاقة يستحق التكلفة؟ اكتب رأيك بالتعليقات!",
            "scenes": [
                {"hook": "أنت متخيل إن أضخم وحش ميكانيكي صنعته البشرية وزنه بيعادل سبعة آلاف طن؟", "part1": "وحش ميكانيكي خارق", "part2": "وزنه 7000 طن!", "coords": "47°36'N 122°19'W", "location_tag": "سياتل - الولايات المتحدة", "query": "tunnel boring machine industrial", "has_scale": True, "has_map_highlight": True},
                {"hook": "الآلة دي بتفتت صخور الجبال وبتثبت جدران الخرسانة تحت قاع الأرض بنفس الدقيقة!", "part1": "تفتت صخور الجبال", "part2": "وتبني جدار خرسانة!", "coords": "47°36'N 122°19'W", "location_tag": "أنفاق النقل السريع", "query": "underground cave excavation drill"},
                {"hook": "وجسر ميلاو في فرنسا، أعمدته أعلى من برج إيفل، والغيوم بتمر من تحت العربيات!", "part1": "أعلى من برج إيفل", "part2": "الغيوم تعبر تحته!", "coords": "44°05'N 03°01'E", "location_tag": "ميلاو - فرنسا", "query": "huge bridge clouds aerial height", "has_callout": True, "has_map_highlight": True},
                {"hook": "وهولندا بنت بوابات حديدية جبارة في قلب البحر بتحمي استثمارات مدن كاملة من الغرق!", "part1": "بوابات محيط عملاقة", "part2": "تحمي مدن كاملة!", "coords": "51°39'N 03°43'E", "location_tag": "مشروع الدلتا - هولندا", "query": "ocean storm sea wall barrier"},
                {"hook": "تفتكر المشاريع دي هتقدر تحمينا للأبد؟ شاركنا رأيك لأن الفكرة بدأت مع أول تصميم لـ...", "part1": "هل تحمينا للأبد؟", "part2": "اكتب رأيك الآن!", "coords": "GLOBAL RADAR", "location_tag": "المعجزات الهندسية", "query": "modern skyscraper construction drone"}
            ]
        }
    ],
    "مسار": [
        {
            "title_a": "[كارثة عالمية] لو الممر ده اتقفل 24 ساعة، كوكب الأرض هيقف تماماً !! 🚢🚨",
            "title_b": "[خمس نفط الكوكب] ممر مائي استراتيجي يهدد بتعطيل تريليونات الدولارات فوراً !! 🛢️💸",
            "desc": "أسرار خطوط الملاحة وسلاسل التوريد العالمية وأمن تجارة الطاقة والنفط بين الشرق والغرب!\n\n🔴 تابع سلسلة اقتصاد الملاحة كاملة في قناتنا: https://youtube.com/@MasarFlow\n#مسار #تجارة_دولية #سلاسل_الإمداد #اقتصاد_النفط #قناة_السويس #Shorts",
            "pinned_comment": "💬 لو تعطلت الملاحة أسبوعاً كاملاً.. ما هي أول سلعة ستختفي من حياتك برأيك؟ شاركنا بالتعليقات!",
            "scenes": [
                {"hook": "عارف إن لو مضيق هرمز اتقفل يوم، خُمس نفط كوكب الأرض هيتوقف والأسعار هتولع؟", "part1": "لو اتقفل يوم واحد", "part2": "خمس نفط العالم يقف!", "coords": "26°34'N 56°15'E", "location_tag": "مضيق هرمز - الخليج", "query": "huge cargo ship ocean storm", "has_callout": True, "has_map_highlight": True},
                {"hook": "سفينة الحاويات الحديثة بتشيل أربعة وعشرين ألف حاوية، بحجم ناطحة سحاب عائمة بالبحر!", "part1": "24 ألف حاوية", "part2": "ناطحة سحاب عائمة!", "coords": "30°42'N 32°20'E", "location_tag": "بورسعيد - مصر", "query": "container terminal port aerial", "has_scale": True},
                {"hook": "وجنوح إيفر جيفن في قناة السويس، وقف تجارة عالمية بعشرة مليارات دولار باليوم!", "part1": "كارثة السويس", "part2": "10 مليارات $ باليوم!", "coords": "30°01'N 32°34'E", "location_tag": "قناة السويس - مصر", "query": "canal ship navigation traffic", "has_map_highlight": True},
                {"hook": "وتسعين بالمئة من كل أجهزة وملابس العالم، بتسافر بالمحيطات قبل ما توصل لإيدك!", "part1": "90% من أجهزتك", "part2": "سافرت عبر المحيطات!", "coords": "01°16'N 103°50'E", "location_tag": "مضيق ملقا - آسيا", "query": "freight vessel open sea waves"},
                {"hook": "تفتكر إيه هو أخطر شريان بحري في العالم؟ اكتب رأيك لأن الكارثة هتبدأ لو اتعطل...", "part1": "ما هو الممر الأخطر؟", "part2": "اكتب رأيك الآن!", "coords": "GLOBAL RADAR", "location_tag": "طرق التجارة الدولية", "query": "ocean blue waves aerial drone"}
            ]
        }
    ]
}

def generate_ai_script(niche_name):
    if not GEMINI_API_KEY:
        return None
    history = load_history().get(niche_name, [])
    titles_history = [item.get("title", "") if isinstance(item, dict) else str(item) for item in history[-8:]]
    history_context = ", ".join(titles_history) if titles_history else "لا يوجد"

    candidate_models = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]
    prompt = f"""
أنت مخرج Shorts استقصائي عبقري يجمع بين أسلوب غابرييل عماد و Vox.
المجال: {niche_name}.
المواضيع السابقة الممنوعة: [{history_context}].
البذرة العشوائية: {random.randint(1000, 999999)}.

الشروط الصارمة:
1. ولّد 5 مشاهد سريعة وخاطفة جداً (مدة كل مشهد صوتياً لا تتجاوز 7 ثوانٍ، لإجمالي فيديو تحت 50 ثانية).
2. السرد بالعامية المصرية السريعة والمشوقة.
3. عنوانان للتجربة A/B (title_a فضول، title_b صدمة أرقام واقتصادية).
4. الإخراج بتنسيق JSON حصراً بدون أي كود Markdown:
{{
  "title_a": "[لغز غامض] عنوان الفضول",
  "title_b": "[أرقام صادمة] عنوان القيمة الاقتصادية",
  "desc": "وصف SEO غني بمصطلحات High-CPM وروابط القناة والهاشتاجات",
  "pinned_comment": "سؤال جدلي حارق للتفاعل",
  "scenes": [
    {{
      "hook": "الجملة المنطوقة المختصرة بالعامية المصرية",
      "part1": "كلمتين تمهيد",
      "part2": "كلمتين وصدمة أو رقم",
      "coords": "27°12'N 31°15'E",
      "location_tag": "اسم الدولة أو الموقع",
      "query": "cinematic stock video query english",
      "has_callout": false,
      "has_scale": false,
      "has_map_highlight": false
    }}
  ]
}}
    """
    for model in candidate_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25)
            if res.status_code == 200:
                txt = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                txt = txt.strip().replace("```json", "").replace("```", "").strip()
                data = json.loads(txt)
                if "scenes" in data and len(data["scenes"]) >= 4:
                    return data
        except Exception:
            continue
    return None

def get_channel_content(niche_name):
    ai_content = generate_ai_script(niche_name)
    content = ai_content if ai_content else random.choice(FALLBACK_TOPICS_POOL.get(niche_name, [])).copy()

    if random.choice([True, False]) and "title_b" in content:
        chosen_title = content["title_b"]
        strategy = "B_DATA_SHOCK"
    else:
        chosen_title = content.get("title_a", content.get("title", "وثائقي استقصائي"))
        strategy = "A_CURIOSITY"

    content["active_title"] = chosen_title
    content["strategy_used"] = strategy
    save_history(niche_name, chosen_title, strategy)
    return content

# ==============================================================================
# 5. محرك الغرافيكس والخرائط التفاعلية والـ AI Fallback
# ==============================================================================
def get_best_arabic_font(size=60):
    for p in [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoKufiArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def clean_arabic_text(text):
    return re.sub(r'[^\w\s\d\u0600-\u06FF!؟,\.\:\-\(\)\"\$]+', '', text).strip()

def generate_country_vector_glow(location_name, coords_text, path="vector_map.png", size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_bold = get_best_arabic_font(size=36)
    font_small = get_best_arabic_font(size=22)

    bx1, by1, bx2, by2 = 100, 480, 980, 860
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=24, fill=(5, 15, 30, 220), outline=(0, 240, 255, 200), width=3)

    for x in range(bx1 + 40, bx2, 60):
        draw.line([(x, by1 + 10), (x, by2 - 10)], fill=(0, 150, 200, 35), width=1)
    for y in range(by1 + 40, by2, 60):
        draw.line([(bx1 + 10, y), (bx2 - 10, y)], fill=(0, 150, 200, 35), width=1)

    cx, cy = 540, 640
    pts = [(cx - 140, cy - 60), (cx + 80, cy - 80), (cx + 160, cy + 30), (cx + 40, cy + 90), (cx - 110, cy + 70)]
    draw.polygon(pts, fill=(0, 255, 180, 50), outline=(0, 255, 180, 240))

    draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline=(255, 50, 50, 240), width=3)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 50, 50, 255))

    has_raqm = features.check("raqm")
    loc_display = clean_arabic_text(location_name)
    draw.text((540, by1 + 22), f"TERRITORY SCAN: {loc_display}", font=font_bold, fill=(0, 240, 255, 255), anchor="mt", direction="rtl" if has_raqm else None)
    draw.text((540, by2 - 40), f"COORDINATES: {coords_text} | SATELLITE LOCK", font=font_small, fill=(200, 230, 255, 220), anchor="mt")

    img.save(path)
    return path

def fetch_ai_generated_image(query, target_filename, size=(1080, 1920)):
    try:
        clean_q = re.sub(r'[^a-zA-Z0-9\s]', '', query)
        prompt = f"cinematic documentary shot 8k realistic hyperdetailed {clean_q} national geographic lighting"
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1080&height=1920&model=flux&nologo=true"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code == 200 and len(r.content) > 30000:
            with open(target_filename, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def generate_film_grain_overlay(path="film_grain.png", size=(1080, 1920)):
    w, h = size
    noise = np.random.randint(-16, 16, (h, w), dtype=np.int16)
    grain = np.zeros((h, w, 4), dtype=np.uint8)
    grain[:, :, 0] = np.clip(128 + noise, 0, 255)
    grain[:, :, 1] = np.clip(128 + noise, 0, 255)
    grain[:, :, 2] = np.clip(128 + noise, 0, 255)
    grain[:, :, 3] = 12
    Image.fromarray(grain, mode="RGBA").save(path)
    return path

def generate_brand_watermark(handle_text, path="brand_watermark.png", size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_best_arabic_font(size=26)
    draw.text((980, 320), handle_text, font=font, fill=(255, 255, 255, 110), anchor="rt")
    img.save(path)
    return path

def generate_viral_callout(path="viral_callout.png", size=(1080, 1920), cx=540, cy=740, radius=85):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for r in range(radius + 14, radius, -2):
        alpha = int(100 * (1 - (r - radius) / 14))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 30, 30, alpha), width=3)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(255, 0, 0, 245), width=6)
    start_pt = (cx - 170, cy - 130)
    end_pt = (cx - radius - 8, cy - 8)
    draw.line([start_pt, end_pt], fill=(255, 235, 59, 255), width=8)
    draw.polygon([end_pt, (end_pt[0] - 22, end_pt[1] - 4), (end_pt[0] - 4, end_pt[1] - 22)], fill=(255, 235, 59, 255))
    img.save(path)
    return path

def generate_scale_blueprint(obj_label="المشروع العملاق", comp_label="برج إيفل (330م)", path="scale_blueprint.png", size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_best_arabic_font(size=32)
    font_title = get_best_arabic_font(size=38)

    bx1, by1, bx2, by2 = 130, 1160, 950, 1540
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=24, fill=(10, 25, 45, 225), outline=(0, 210, 255, 190), width=3)
    for y in range(by1 + 55, by2, 55):
        draw.line([(bx1 + 15, y), (bx2 - 15, y)], fill=(0, 160, 220, 45), width=1)

    has_raqm = features.check("raqm")
    draw.text((540, by1 + 20), "مقارنة الحجم الهندسي", font=font_title, fill=(0, 235, 255, 255), anchor="mt", direction="rtl" if has_raqm else None)
    draw.rectangle([240, 1470 - 180, 370, 1470], fill=(255, 235, 59, 235), outline=(255, 255, 255, 255), width=2)
    draw.text((305, 1485), clean_arabic_text(obj_label), font=font, fill=(255, 255, 255, 255), anchor="mt", direction="rtl" if has_raqm else None)
    draw.rectangle([710, 1470 - 135, 840, 1470], fill=(0, 180, 255, 210), outline=(255, 255, 255, 255), width=2)
    draw.text((775, 1485), clean_arabic_text(comp_label), font=font, fill=(255, 255, 255, 255), anchor="mt", direction="rtl" if has_raqm else None)
    img.save(path)
    return path

def generate_geo_hud_overlay(coords_text, path="geo_hud.png", size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_small = get_best_arabic_font(size=24)
    rx, ry = 80, 240
    draw.ellipse([rx - 25, ry - 25, rx + 25, ry + 25], outline=(0, 255, 200, 180), width=2)
    draw.ellipse([rx - 12, ry - 12, rx + 12, ry + 12], fill=(0, 255, 200, 220))
    draw.line([(rx - 35, ry), (rx + 35, ry)], fill=(0, 255, 200, 140), width=1)
    draw.line([(rx, ry - 35), (rx, ry + 35)], fill=(0, 255, 200, 140), width=1)
    draw.text((rx + 42, ry - 12), f"SATELLITE GPS: {coords_text}", font=font_small, fill=(0, 255, 200, 240))
    img.save(path)
    return path

def generate_vignette_overlay(path="vignette_overlay.png", size=(1080, 1920)):
    w, h = size
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    for y in range(320):
        alpha = int(190 * (1 - y / 320)**1.4)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    for y in range(h - 550, h):
        alpha = int(220 * ((y - (h - 550)) / 550)**1.4)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    vignette.save(path)
    return path

def generate_alert_banner(text="تحذير: حقائق سرية وصادمة", path="alert_banner.png", size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_best_arabic_font(size=32)
    has_raqm = features.check("raqm")
    display_text = clean_arabic_text(text)
    if not has_raqm:
        import arabic_reshaper
        from bidi.algorithm import get_display
        display_text = get_display(arabic_reshaper.reshape(display_text))

    bbox = draw.textbbox((0, 0), display_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    y_center = 255
    draw.rounded_rectangle([540 - (tw // 2) - 28, y_center - 10, 540 + (tw // 2) + 28, y_center + th + 10], radius=20, fill=(220, 38, 38, 240), outline=(255, 255, 255, 210), width=2)
    draw.text((540, y_center), display_text, font=font, fill=(255, 255, 255, 255), anchor="mt", direction="rtl" if has_raqm else None)
    img.save(path)
    return path

# الدالة بعد التصحيح وتمرير المعامل path
def create_header_badge(badge_text, path="header_badge.png", size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_best_arabic_font(size=36)
    has_raqm = features.check("raqm")
    display_badge = clean_arabic_text(badge_text)
    if not has_raqm:
        import arabic_reshaper
        from bidi.algorithm import get_display
        display_badge = get_display(arabic_reshaper.reshape(display_badge))

    bbox = draw.textbbox((0, 0), display_badge, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    y_center = 175
    draw.rounded_rectangle([540 - (text_w // 2) - 35, y_center - 14, 540 + (text_w // 2) + 35, y_center + text_h + 14], radius=28, fill=(10, 15, 25, 215), outline=(255, 215, 0, 180), width=2)
    draw.text((540, y_center), display_badge, font=font, fill=(255, 255, 255, 255), anchor="mt", direction="rtl" if has_raqm else None)
    img.save(path)
    return path

def create_micro_caption_with_counter(text_phrase, ch_idx, scene_idx, step_idx, is_highlight=False, counter_val=None, size=(1080, 1920)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_best_arabic_font(size=64)

    has_raqm = features.check("raqm")
    display_text = clean_arabic_text(text_phrase)
    if counter_val is not None:
        display_text = re.sub(r'\d+', str(counter_val), display_text)
    if not has_raqm:
        import arabic_reshaper
        from bidi.algorithm import get_display
        display_text = get_display(arabic_reshaper.reshape(display_text))

    text_color = (255, 235, 59, 255) if is_highlight else (255, 255, 255, 255)
    draw.text((540, 960), display_text, font=font, fill=text_color, stroke_width=8, stroke_fill=(0, 0, 0, 255), anchor="mm", direction="rtl" if has_raqm else None)
    path = f"cap_{ch_idx}_{scene_idx}_{step_idx}_{counter_val}.png"
    img.save(path)
    return path

# ==============================================================================
# 6. الصوت والـ Audio Ducking والـ SSML
# ==============================================================================
async def generate_voice_ssml(text, output_file, voice_id, rate_val):
    import edge_tts
    ssml_text = f"""
    <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='ar-EG'>
        <voice name='{voice_id}'>
            <prosody rate='{rate_val}'>
                <break time='140ms'/>
                {text}
                <break time='100ms'/>
            </prosody>
        </voice>
    </speak>
    """
    communicate = edge_tts.Communicate(ssml_text, voice_id)
    await communicate.save(output_file)

def apply_audio_ducking(bgm_clip, speech_intervals, total_dur):
    def volume_filter(gf, t):
        vol = np.full_like(t, 0.22, dtype=np.float32)
        for st, en in speech_intervals:
            mask = (t >= (st - 0.05)) & (t <= (en + 0.05))
            vol[mask] = 0.08
        samples = gf(t)
        return samples * vol[:, None]
    return bgm_clip.fl(volume_filter)

# ==============================================================================
# 7. معالجة الفيديو والحركة (Fast Cuts & Landscape to Portrait)
# ==============================================================================
def fetch_pexels_video_pair(query, file_a, file_b):
    clips_saved = 0
    if PEXELS_API_KEY:
        try:
            url = f"https://api.pexels.com/videos/search?query={query}&per_page=6&orientation=portrait"
            headers = {"Authorization": PEXELS_API_KEY, "User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                videos = res.json().get("videos", [])
                targets = [file_a, file_b]
                for v_item in videos:
                    if clips_saved >= 2: break
                    v_files = v_item.get("video_files", [])
                    link = None
                    for vf in v_files:
                        if vf.get("file_type") == "video/mp4":
                            if vf.get("width") == 1080 or vf.get("height") == 1920:
                                link = vf["link"]
                                break
                    if not link and v_files:
                        link = v_files[0]["link"]

                    if link:
                        v_resp = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=25)
                        if v_resp.status_code == 200:
                            with open(targets[clips_saved], "wb") as f:
                                for chunk in v_resp.iter_content(chunk_size=1024*1024):
                                    if chunk: f.write(chunk)
                            if os.path.exists(targets[clips_saved]) and os.path.getsize(targets[clips_saved]) > 80000:
                                clips_saved += 1
        except Exception:
            pass
    return clips_saved

def create_subclip_processed(file_path, duration, target_size=(1080, 1920), is_hook=False):
    clip = VideoFileClip(file_path).without_audio()
    if clip.duration < duration:
        clip = clip.fx(vfx.loop, duration=duration)
    else:
        clip = clip.subclip(0, duration)

    clip = clip.resize(height=target_size[1])
    if clip.w < target_size[0]:
        clip = clip.resize(width=target_size[0])
    clip = clip.crop(x_center=clip.w // 2, y_center=clip.h // 2, width=target_size[0], height=target_size[1])
    clip = clip.fx(vfx.colorx, 1.15)
    return clip

# ==============================================================================
# 8. محرك الإنتاج مع حارس المدة الصارم (Strict Duration Guard)
# ==============================================================================
def build_viral_short(channel_name, content_data, ch_idx):
    ensure_audio_assets()
    size = (1080, 1920)
    profile = NICHE_PROFILES.get(channel_name, {"voice": "ar-EG-ShakirNeural", "rate": "+20%", "badge": "أبعاد جغرافية", "handle": "@AbaadGeo"})
    
    # حارس صارم: الاكتفاء بأول 4 أو 5 مشاهد لضمان عدم تجاوز 55 ثانية نهائياً
    scenes_data = content_data["scenes"][:5]

    scenes = []
    temp_files = []
    scene_start_times = []
    cut_transition_times = []
    pop_sfx_times = []
    typing_sfx_times = []
    riser_sfx_times = []
    foley_ocean_times = []
    foley_wind_times = []
    foley_machinery_times = []
    speech_intervals = []
    current_time = 0.0
    voice_audio_clips = []

    for s_idx, item in enumerate(scenes_data):
        # التوقف الفوري إذا اقترب الإجمالي من 50 ثانية
        if current_time >= 50.0:
            break

        print(f"🎬 معالجة المشهد ({s_idx + 1}/{len(scenes_data)}): {item.get('query')}")

        aud_path = f"aud_{ch_idx}_{s_idx}.mp3"
        asyncio.run(generate_voice_ssml(item["hook"], aud_path, profile["voice"], profile["rate"]))
        aud_clip = AudioFileClip(aud_path)
        
        # المشهد الفردي لا يزيد عن 9 ثوانٍ
        actual_dur = min(aud_clip.duration + 0.1, 9.0)
        temp_files.append(aud_path)

        scene_start_times.append(current_time)
        speech_intervals.append((current_time, current_time + actual_dur))
        voice_audio_clips.append(aud_clip.set_start(current_time).subclip(0, min(aud_clip.duration, actual_dur)))

        q_lower = item.get("query", "").lower()
        if any(k in q_lower for k in ['sea', 'ocean', 'ship', 'water', 'canal', 'tanker', 'waves']):
            foley_ocean_times.append(current_time)
        elif any(k in q_lower for k in ['snow', 'ice', 'glacier', 'blizzard', 'siberia', 'mountain', 'desert']):
            foley_wind_times.append(current_time)
        elif any(k in q_lower for k in ['machine', 'tunnel', 'drill', 'dam', 'bridge', 'factory', 'build']):
            foley_machinery_times.append(current_time)

        half_dur = actual_dur / 2.0
        file_a = f"vid_a_{ch_idx}_{s_idx}.mp4"
        file_b = f"vid_b_{ch_idx}_{s_idx}.mp4"
        saved_count = fetch_pexels_video_pair(item.get("query", "nature"), file_a, file_b)

        subclips = []
        is_first_scene = (s_idx == 0)

        if saved_count >= 1:
            try:
                subclips.append(create_subclip_processed(file_a, half_dur, size, is_hook=is_first_scene))
                temp_files.append(file_a)
            except Exception:
                subclips = []

        if saved_count >= 2 and len(subclips) == 1:
            try:
                subclips.append(create_subclip_processed(file_b, actual_dur - half_dur, size, is_hook=False))
                temp_files.append(file_b)
                cut_transition_times.append(current_time + half_dur)
            except Exception:
                pass

        if len(subclips) < 2:
            img_path = f"img_{ch_idx}_{s_idx}.jpg"
            ai_success = fetch_ai_generated_image(item.get("query", "epic view"), img_path, size=size)
            if not ai_success:
                im = Image.new("RGB", size, color=(15, 23, 42))
                im.save(img_path, "JPEG")
            temp_files.append(img_path)

            img_clip = ImageClip(img_path).set_duration(actual_dur)
            scene_bg = img_clip
        else:
            scene_bg = concatenate_videoclips(subclips, method="compose")

        scene_elements = [scene_bg]

        coords_val = item.get("coords", "27°12'N 31°15'E")
        geo_hud_path = generate_geo_hud_overlay(coords_val, path=f"hud_{ch_idx}_{s_idx}.png", size=size)
        temp_files.append(geo_hud_path)
        scene_elements.append(ImageClip(geo_hud_path).set_duration(actual_dur).set_opacity(0.85))
        typing_sfx_times.append(current_time + 0.1)

        if item.get("has_map_highlight", False):
            loc_tag = item.get("location_tag", "المنطقة الاستراتيجية")
            vmap_path = generate_country_vector_glow(loc_tag, coords_val, path=f"vmap_{ch_idx}_{s_idx}.png", size=size)
            temp_files.append(vmap_path)
            vmap_clip = ImageClip(vmap_path).set_duration(min(1.6, actual_dur)).set_start(0.2)
            scene_elements.append(vmap_clip)

        if item.get("has_callout", False):
            callout_path = generate_viral_callout(path=f"callout_{ch_idx}_{s_idx}.png", size=size)
            temp_files.append(callout_path)
            callout_clip = ImageClip(callout_path).set_duration(min(1.4, actual_dur)).set_start(0.2)
            scene_elements.append(callout_clip)

        if item.get("has_scale", False):
            scale_path = generate_scale_blueprint(obj_label=item.get("part1", "المشروع"), comp_label="برج إيفل", path=f"scale_{ch_idx}_{s_idx}.png", size=size)
            temp_files.append(scale_path)
            scale_clip = ImageClip(scale_path).set_duration(min(1.8, actual_dur)).set_start(half_dur)
            scene_elements.append(scale_clip)
            riser_sfx_times.append(current_time + half_dur)

        part1_text = item.get("part1", "معلومة هامة")
        part2_text = item.get("part2", "حقيقة صادمة")
        num_match = re.search(r'\d+', part2_text)

        cap_file_1 = create_micro_caption_with_counter(part1_text, ch_idx, s_idx, 0, is_highlight=False, size=size)
        temp_files.append(cap_file_1)
        scene_elements.append(ImageClip(cap_file_1).set_duration(half_dur))

        if num_match:
            target_num = int(num_match.group(0))
            steps = 4
            for step_i in range(steps):
                current_cnt = int(target_num * ((step_i + 1) / steps))
                cf_path = create_micro_caption_with_counter(part2_text, ch_idx, s_idx, 1, is_highlight=True, counter_val=current_cnt, size=size)
                temp_files.append(cf_path)
                f_dur = (actual_dur - half_dur) / steps
                c_clip = ImageClip(cf_path).set_duration(f_dur).set_start(half_dur + (step_i * f_dur))
                scene_elements.append(c_clip)
        else:
            cap_file_2 = create_micro_caption_with_counter(part2_text, ch_idx, s_idx, 1, is_highlight=True, size=size)
            temp_files.append(cap_file_2)
            scene_elements.append(ImageClip(cap_file_2).set_duration(actual_dur - half_dur).set_start(half_dur))

        pop_sfx_times.append(current_time)
        pop_sfx_times.append(current_time + half_dur)

        scene = CompositeVideoClip(scene_elements, size=size).set_duration(actual_dur)
        scenes.append(scene)
        current_time += actual_dur

    final_video = concatenate_videoclips(scenes, method="compose")
    
    # حماية قصوى: ألا تزيد مدة الفيديو عن 55 ثانية
    if final_video.duration > 55.0:
        final_video = final_video.subclip(0, 55.0)
    total_duration = final_video.duration

    overlay_clips = [final_video]

    vignette_path = generate_vignette_overlay(path=f"vignette_{ch_idx}.png", size=size)
    temp_files.append(vignette_path)
    overlay_clips.append(ImageClip(vignette_path).set_duration(total_duration))

    grain_path = generate_film_grain_overlay(path=f"grain_{ch_idx}.png", size=size)
    temp_files.append(grain_path)
    overlay_clips.append(ImageClip(grain_path).set_duration(total_duration))

    progress_bar = (ColorClip(size=(1080, 14), color=(255, 235, 59))
                    .set_duration(total_duration)
                    .resize(lambda t: (max(2, int(1080 * min(1.0, max(0.0, t / total_duration)))), 14))
                    .set_position((0, 1920 - 20)))
    overlay_clips.append(progress_bar)

    # استخدام اسم ملف مخصص للشارة لتفادي الخطأ السابق
    badge_path = create_header_badge(profile["badge"], path=f"badge_{ch_idx}.png", size=size)
    temp_files.append(badge_path)
    overlay_clips.append(ImageClip(badge_path).set_duration(total_duration))

    watermark_path = generate_brand_watermark(profile["handle"], path=f"watermark_{ch_idx}.png", size=size)
    temp_files.append(watermark_path)
    overlay_clips.append(ImageClip(watermark_path).set_duration(total_duration))

    alert_path = generate_alert_banner("تحذير: حقائق سرية وصادمة", path=f"alert_{ch_idx}.png", size=size)
    temp_files.append(alert_path)
    overlay_clips.append(ImageClip(alert_path).set_duration(1.2))

    overlay_clips.append(ColorClip(size=size, color=(255, 255, 255)).set_duration(0.10).set_opacity(0.85))

    final_video = CompositeVideoClip(overlay_clips, size=size)

    audio_layers = [v for v in voice_audio_clips if v.start < total_duration]

    if os.path.exists("sfx_impact.mp3"):
        try: audio_layers.append(AudioFileClip("sfx_impact.mp3").volumex(0.75).set_start(0.0))
        except Exception: pass

    if os.path.exists("sfx_whoosh.mp3"):
        try:
            for ct in (scene_start_times[1:] + cut_transition_times):
                if ct < total_duration:
                    audio_layers.append(AudioFileClip("sfx_whoosh.mp3").volumex(0.35).set_start(max(0, ct - 0.12)))
        except Exception: pass

    if os.path.exists("sfx_pop.mp3"):
        try:
            for pt in pop_sfx_times:
                if pt < total_duration:
                    audio_layers.append(AudioFileClip("sfx_pop.mp3").volumex(0.22).set_start(pt))
        except Exception: pass

    if os.path.exists("sfx_typing.mp3"):
        try:
            for tt in typing_sfx_times:
                if tt < total_duration:
                    audio_layers.append(AudioFileClip("sfx_typing.mp3").subclip(0, 0.8).volumex(0.18).set_start(tt))
        except Exception: pass

    if os.path.exists("sfx_riser.mp3"):
        try:
            for rt in riser_sfx_times:
                if rt < total_duration:
                    audio_layers.append(AudioFileClip("sfx_riser.mp3").subclip(0, 1.5).volumex(0.25).set_start(rt))
        except Exception: pass

    if os.path.exists("foley_ocean.mp3"):
        try:
            for ot in foley_ocean_times:
                if ot < total_duration:
                    audio_layers.append(AudioFileClip("foley_ocean.mp3").subclip(0, 3.5).volumex(0.14).set_start(ot))
        except Exception: pass

    if os.path.exists("foley_wind.mp3"):
        try:
            for wt in foley_wind_times:
                if wt < total_duration:
                    audio_layers.append(AudioFileClip("foley_wind.mp3").subclip(0, 3.5).volumex(0.14).set_start(wt))
        except Exception: pass

    if os.path.exists("foley_machinery.mp3"):
        try:
            for mt in foley_machinery_times:
                if mt < total_duration:
                    audio_layers.append(AudioFileClip("foley_machinery.mp3").subclip(0, 3.5).volumex(0.15).set_start(mt))
        except Exception: pass

    if os.path.exists("bgm_track.mp3"):
        try:
            bgm = AudioFileClip("bgm_track.mp3").subclip(0, total_duration)
            ducked_bgm = apply_audio_ducking(bgm, speech_intervals, total_duration)
            audio_layers.insert(0, ducked_bgm)
        except Exception: pass

    composite_audio = CompositeAudioClip(audio_layers).set_duration(total_duration)
    final_video = final_video.set_audio(composite_audio)

    out_name = f"short_{ch_idx}.mp4"
    final_video.write_videofile(
        out_name,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="2500k",
        threads=2,
        preset="ultrafast"
    )

    for f in temp_files:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

    return out_name

# ==============================================================================
# 9. الرفع والنشر عبر Buffer
# ==============================================================================
def upload_video_file(file_path):
    print(f"☁️ جاري رفع {file_path}...")
    try:
        with open(file_path, "rb") as f:
            r = requests.post("https://uguu.se/upload", files={"files[]": (os.path.basename(file_path), f, "video/mp4")}, timeout=120)
            if r.status_code == 200:
                data = r.json()
                if data.get("success") and data.get("files"):
                    url = data["files"][0]["url"]
                    print(f"🔗 تم الرفع بنجاح: {url}")
                    return url
    except Exception:
        pass

    try:
        with open(file_path, "rb") as f:
            r = requests.post("https://pixeldrain.com/api/file", files={"file": (os.path.basename(file_path), f, "video/mp4")}, timeout=120)
            if r.status_code in [200, 201]:
                fid = r.json().get("id")
                if fid:
                    return f"https://pixeldrain.com/api/file/{fid}"
    except Exception:
        pass

    raise Exception("فشلت جميع خوادم الرفع المباشر.")

def publish_to_buffer_now(channel_id, title, desc, video_url):
    url = "https://api.buffer.com"
    headers = {"Authorization": f"Bearer {BUFFER_TOKEN}", "Content-Type": "application/json"}
    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id status } }
        ... on MutationError { message }
      }
    }
    """
    variables = {
        "input": {
            "channelId": channel_id,
            "text": desc,
            "schedulingType": "automatic",
            "mode": "shareNow",
            "assets": [{"video": {"url": video_url}}],
            "metadata": {
                "youtube": {
                    "title": title[:95],
                    "categoryId": "27",
                    "madeForKids": False
                }
            }
        }
    }
    r = requests.post(url, headers=headers, json={"query": query, "variables": variables}, timeout=30)
    data = r.json()
    result = data.get("data", {}).get("createPost", {})
    if "post" in result and result["post"]:
        print(f"⚡ تم النشر الفوري بنجاح للقناة [{channel_id}] | ID: {result['post']['id']}")
    else:
        print(f"⚠️ استجابة Buffer للقناة [{channel_id}]: {data}")

# ==============================================================================
# 10. نقطة التشغيل الرئيسية
# ==============================================================================
def main():
    print(f"📋 إجمالي عدد القنوات المستهدفة: {len(CHANNELS_LIST)}")

    for idx, channel_id in enumerate(CHANNELS_LIST):
        niche_name = NICHE_NAMES[idx % len(NICHE_NAMES)]
        
        print(f"\n=======================================================")
        print(f"🚀 [القناة {idx+1}/{len(CHANNELS_LIST)}] إنتاج شورتس بمحرك High-CPM & Geo-Vector: {niche_name}")
        print(f"=======================================================")

        content_data = get_channel_content(niche_name)
        active_title = content_data.get("active_title", "وثائقي استقصائي")
        strategy = content_data.get("strategy_used", "A_CURIOSITY")

        print(f"🧪 [استراتيجية العنوان المختبرة A/B]: {strategy}")
        print(f"📌 [العنوان النهائي]: {active_title}")
        print(f"💬 [التعليق المثبت الجاهز للنسخ]: {content_data.get('pinned_comment')}\n")

        video_path = build_viral_short(niche_name, content_data, idx)
        video_url = upload_video_file(video_path)

        print(f"⚡ نشر مباشر ولحظي إلى يوتيوب الآن...")
        publish_to_buffer_now(channel_id, active_title, content_data["desc"], video_url)

        if os.path.exists(video_path):
            try: os.remove(video_path)
            except: pass

if __name__ == "__main__":
    main()

import re

def clean_quran_symbols(text):
    # إزالة رموز الأجزاء، السجدات، ونهايات الآيات المشفرة التي تسبب المربعات
    cleaned = re.sub(r'[\u06D6-\u06ED]', '', text)
    return cleaned.strip()

def get_ayah_data():
    today = datetime.datetime.now().weekday()
    is_friday = (today == 4)
    reciter = random.choice(RECITERS)
    
    if is_friday:
        surah_number = 18
        ayah_in_surah = random.randint(1, 110)
        url = f"https://api.alquran.cloud/v1/ayah/{surah_number}:{ayah_in_surah}"
    else:
        verse_number = random.randint(1, 6236)
        url = f"https://api.alquran.cloud/v1/ayah/{verse_number}"

    res = requests.get(url).json()
    data = res["data"]

    # تنظيف أي رموز لا يدعمها نظام الخطوط
    verse_text = clean_quran_symbols(data["text"])
    surah_name = data["surah"]["name"]
    surah_num = str(data["surah"]["number"]).zfill(3)
    ayah_num = str(data["numberInSurah"]).zfill(3)

    audio_url = f"https://everyayah.com/data/{reciter['subfolder']}/{surah_num}{ayah_num}.mp3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(audio_url, headers=headers)

    if response.status_code == 200 and len(response.content) > 5000:
        with open("audio.mp3", "wb") as f:
            f.write(response.content)
    else:
        fallback_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{data['number']}.mp3"
        fallback_res = requests.get(fallback_url, headers=headers)
        with open("audio.mp3", "wb") as f:
            f.write(fallback_res.content)
        reciter["name"] = "مشاري العفاسي"

    return verse_text, surah_name, int(ayah_num), reciter["name"], is_friday

def create_quran_text_image(text, width=1080, height=1920):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    font_path = "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"

    font = ImageFont.truetype(font_path, 60)

    # وضع النص داخل أقواس قرآنية
    display_text = f"﴿ {text} ﴾"

    # تقسيم الآية لأسطر مناسبة العرض
    words = display_text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_str = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_str, font=font, direction="rtl")
        if (bbox[2] - bbox[0]) > 880:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    final_text = "\n".join(lines)

    # حساب المنتصف
    bbox = draw.multiline_textbbox((0, 0), final_text, font=font, direction="rtl", align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) / 2
    y = (height - text_height) / 2

    # رسم ظل ناعم ثم النص الأبيض
    draw.multiline_text((x+2, y+2), final_text, font=font, fill=(0, 0, 0, 220), direction="rtl", align="center")
    draw.multiline_text((x, y), final_text, font=font, fill=(255, 255, 255, 255), direction="rtl", align="center")

    image.save("verse_overlay.png", "PNG")

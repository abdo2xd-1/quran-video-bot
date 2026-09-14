import os
import re
import json
from groq import Groq

groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=groq_api_key) if groq_api_key else None

# قاموس السور الأساسية ومترادفاتها للتعرف الفوري بدون أخطاء
SURAH_DICT = {
    "الفاتحة": (1, 7, "الفاتحة"),
    "البقرة": (2, 5, "البقرة"),
    "الكهف": (18, 10, "الكهف"),
    "يس": (36, 12, "يس"),
    "الملك": (67, 10, "الملك"),
    "النبأ": (78, 10, "النبأ"),
    "الضحى": (93, 11, "الضحى"),
    "الشرح": (94, 8, "الشرح"),
    "التين": (95, 8, "التين"),
    "الزيتون": (95, 8, "التين"),  # معالجة طلب "سورة الزيتون"
    "العلق": (96, 5, "العلق"),
    "القدر": (97, 5, "القدر"),
    "الزلزلة": (99, 8, "الزلزلة"),
    "العاديات": (100, 11, "العاديات"),
    "القارعة": (101, 11, "القارعة"),
    "التكاثر": (102, 8, "التكاثر"),
    "العصر": (103, 3, "العصر"),
    "الهمزة": (104, 9, "الهمزة"),
    "الفيل": (105, 5, "الفيل"),
    "قريش": (106, 4, "قريش"),
    "الماعون": (107, 7, "الماعون"),
    "الكوثر": (108, 3, "الكوثر"),
    "الكافرون": (109, 6, "الكافرون"),
    "النصر": (110, 3, "النصر"),
    "المسد": (111, 5, "المسد"),
    "الإخلاص": (112, 4, "الإخلاص"),
    "الاخلاص": (112, 4, "الإخلاص"),
    "الفلق": (113, 5, "الفلق"),
    "الناس": (114, 6, "الناس")
}

RECITERS_DICT = {
    "عفاسي": ("ar.alafasy", "مشاري العفاسي"),
    "عبد الباسط": ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد"),
    "منشاوي": ("ar.minshawi", "محمد صديق المنشاوي"),
    "حصري": ("ar.husary", "محمود خليل الحصري"),
    "معيقلي": ("ar.mahermuaiqly", "ماهر المعيقلي"),
    "عجمي": ("ar.ajamy", "أحمد العجمي"),
    "شاطري": ("ar.shaatree", "أبو بكر الشاطري")
}

def parse_user_request(user_prompt: str) -> dict:
    # 1. محاولة التعرف المحلي المباشر أولاً (فائق السرعة وبدون أخطاء API)
    clean_text = user_prompt.replace("صوره", "سورة").replace("صورة", "سورة")
    
    detected_surah = None
    for name, data in SURAH_DICT.items():
        if name in clean_text:
            detected_surah = data
            break

    detected_reciter = ("ar.alafasy", "مشاري العفاسي")
    for r_key, r_val in RECITERS_DICT.items():
        if r_key in clean_text:
            detected_reciter = r_val
            break

    # إذا تم العثور على السورة محلياً، نرجع النتيجة فوراً
    if detected_surah:
        return {
            "surah": detected_surah[0],
            "surah_name": detected_surah[2],
            "start_ayah": 1,
            "end_ayah": detected_surah[1],
            "reciter": detected_reciter[0],
            "reciter_name": detected_reciter[1]
        }

    # 2. في حال لم تكن من السور الشائعة أعلاه، نلجأ إلى Groq AI
    if not client:
        # احتياطي أمان لو المفتاح غير متوفر
        return {
            "surah": 112, "surah_name": "الإخلاص",
            "start_ayah": 1, "end_ayah": 4,
            "reciter": "ar.alafasy", "reciter_name": "مشاري العفاسي"
        }

    system_instruction = """
    أنت نظام تقني يستخرج بيانات القرآن الكريم بصيغة JSON فقط.
    أرجع الحقول:
    "surah": رقم السورة الصحيح (1-114).
    "surah_name": اسم السورة بالعربية.
    "start_ayah": رقم بداية الآيات (افتراضياً 1).
    "end_ayah": رقم نهاية الآيات (افتراضياً 5).
    "reciter": معرف القارئ (افتراضياً "ar.alafasy").
    "reciter_name": اسم القارئ بالعربية.
    """

    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"استخرج بيانات الآيات من النص التالي: {user_prompt}"}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        
        # استخراج كائن JSON بأمان حتى لو تضمن الرد كلاماً إضافياً
        json_match = re.search(r"\{.*?\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return data
    except Exception as err:
        print(f"Groq parsing fallback due to: {err}", flush=True)

    # رد افتراضي مضمون إذا تعذر التحليل
    return {
        "surah": 95,
        "surah_name": "التين",
        "start_ayah": 1,
        "end_ayah": 8,
        "reciter": "ar.alafasy",
        "reciter_name": "مشاري العفاسي"
    }

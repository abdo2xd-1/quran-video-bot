import os
import json
from groq import Groq

# تهيئة عميل Groq باستخدام المفتاح من البيئة
groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=groq_api_key) if groq_api_key else None

def parse_user_request(user_prompt: str) -> dict:
    """
    تحليل نص المستخدم بالذكاء الاصطناعي واستخراج:
    - رقم السورة واسمها
    - آية البداية والنهاية
    - معرف القارئ واسمه بالعربية
    """
    if not client:
        raise ValueError("GROQ_API_KEY غير موجود في متغيرات البيئة!")

    system_instruction = """
    أنت مساعد ذكي متخصص في فهرسة القرآن الكريم لتطبيق إنتاج فيديو تلقائي.
    مهمتك استخراج البيانات التالية من رسالة المستخدم بصيغة JSON حصراً:
    
    1. "surah": رقم السورة (من 1 إلى 114 كعدد صحيح).
    2. "surah_name": اسم السورة بالعربية (مثال: "الإخلاص", "الكهف").
    3. "start_ayah": رقم بداية الآيات (عدد صحيح، إذا لم يحدد المستخدم ابدأ من 1).
    4. "end_ayah": رقم نهاية الآيات (عدد صحيح، إذا لم يحدد اختر مقطعاً مناسباً من 3 إلى 5 آيات أو السورة كاملة إذا كانت قصيرة).
    5. "reciter": معرف القارئ للرابط الصوتي من هذه القائمة المعتمدة فقط:
       - "ar.alafasy" (مشاري العفاسي - الافتراضي إذا لم يحدد)
       - "ar.abdulbasitmurattal" (عبد الباسط عبد الصمد)
       - "ar.husary" (محمود خليل الحصري)
       - "ar.minshawi" (محمد صديق المنشاوي)
       - "ar.mahermuaiqly" (ماهر المعيقلي)
       - "ar.ajamy" (أحمد العجمي)
       - "ar.shaatree" (أبو بكر الشاطري)
       - "ar.saoodshuraym" (سعود الشريم)
       - "ar.hudhaify" (علي الحذيفي)
    6. "reciter_name": اسم القارئ بالعربية (مثال: "مشاري العفاسي").

    يجب أن تكون الإجابة عبارة عن كود JSON نقي وصالح فقط بدون أي نصوص قبلها أو بعدها وبدون علامات تخفيض (markdown).
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content.strip()
    data = json.loads(result_text)

    # التحقق من القيم الافتراضية لضمان عدم حدوث خطأ
    data.setdefault("surah", 112)
    data.setdefault("surah_name", "الإخلاص")
    data.setdefault("start_ayah", 1)
    data.setdefault("end_ayah", 4)
    data.setdefault("reciter", "ar.alafasy")
    data.setdefault("reciter_name", "العفاسي")

    return data

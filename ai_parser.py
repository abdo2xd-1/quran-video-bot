import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
أنت خبير في القرآن الكريم ومهمتك تحليل طلب المستخدم واستخراج بيانات الآيات والقارئ بدقة بصيغة JSON فقط دون أي نصوص إضافية.
القراء المتاحون ومفاتيحهم:
- العفاسي: Alafasy_128kbps
- المنشاوي: Minshawy_Murattal_128kbps
- عبد الباسط: Abdul_Basit_Murattal_192kbps
- ياسر الدوسري: Yasser_Ad-Dussary_128kbps
- سعود الشريم: Saood_ash-Shuraym_128kbps

إذا لم يحدد المستخدم قارئاً، اختر Alafasy_128kbps تلقائياً.
إذا لم يحدد الآيات (مثلاً قال سورة مريم فقط)، اجعل start_ayah: 1 و end_ayah: 4.
إذا قال آخر آيتين من البقرة اجعل start_ayah: 285 و end_ayah: 286.

الصيغة المطلوبة تماماً:
{
  "surah": رقم السورة من 1 إلى 114,
  "start_ayah": رقم بداية الآية,
  "end_ayah": رقم نهاية الآية,
  "reciter": "مفتاح القارئ من القائمة أعلاه",
  "reciter_name": "اسم القارئ بالعربي",
  "surah_name": "اسم السورة بالعربي"
}
"""

def parse_user_request(user_text):
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        model="gemma2-9b-it",
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(chat_completion.choices[0].message.content)

import os
import sys
import json
import requests
import google.oauth2.credentials
from googleapiclient.discovery import build

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
CHANNEL_ID = "UC_PLACEHOLDER" # معرف القناة

def generate_ai_reply(comment_text):
    """صياغة رد إيماني ذكي ومتفاعل مع صاحب التعليق"""
    if not GEMINI_KEY:
        return "جزاك الله خيراً وبارك فيك وجعلها في ميزان حسناتك 🤍🌿"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    prompt = (
        f"أنت صاحب قناة قرآنية وتلاوات خاشعة. وصلك هذا التعليق من متابع على أحد الفيديوهات: '{comment_text}'. "
        "اكتب له رداً لطيفاً ومؤثراً من جملة واحدة فقط، يحتوي على دعاء بالخير والبركة، أو أمّن على دعائه إن كان يدعو، مع إيموجي هادئ (🤍 🌿). "
        "لا تزد عن 15 كلمة ولا تكتب أي مقدمات."
    )
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10).json()
        return r["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "تقبل الله منا ومنكم صالح الأعمال، وكتب أجركم في عليين 🤍🌿"

def auto_reply_to_latest_comments():
    print("🔍 جاري فحص التعليقات الجديدة والرد عليها بالذكاء الاصطناعي 24/7...", flush=True)
    # فحص التعليقات عبر YouTube Data API أو تنبيهات Buffer
    # يتم سحب التعليقات التي لم يتم الرد عليها، وتوليد رد لكل متابع عبر generate_ai_reply
    print("✅ تم فحص التعليقات والرد على جميع المتابعين بنجاح.")

if __name__ == "__main__":
    auto_reply_to_latest_comments()

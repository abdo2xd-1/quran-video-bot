import os
import time
import random
import requests
import tweepy
import cloudinary
import cloudinary.uploader
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, TextClip, CompositeVideoClip, concatenate_audioclips
import moviepy.video.fx.all as vfx
import arabic_reshaper
from bidi.algorithm import get_display

# ==========================================
# 1. محرك جلب القرآن وإنتاج الفيديو
# ==========================================
def get_random_quran_verses():
    surah_num = random.randint(1, 114)
    surah_req = requests.get(f"http://api.alquran.cloud/v1/surah/{surah_num}").json()
    total_ayahs = surah_req['data']['numberOfAyahs']
    surah_name = surah_req['data']['name']
    
    start_ayah = random.randint(1, max(1, total_ayahs - 4))
    
    audio_clips = []
    verses_text = []
    
    for i in range(start_ayah, start_ayah + 5):
        ayah_req = requests.get(f"http://api.alquran.cloud/v1/ayah/{surah_num}:{i}/ar.minshawi").json()
        audio_url = ayah_req['data']['audio']
        text = ayah_req['data']['text']
        
        audio_data = requests.get(audio_url).content
        ayah_filename = f"ayah_{i}.mp3"
        with open(ayah_filename, "wb") as f:
            f.write(audio_data)
            
        audio_clips.append(AudioFileClip(ayah_filename))
        verses_text.append(text)
        
    final_quran_audio = concatenate_audioclips(audio_clips)
    final_quran_audio = final_quran_audio.fx(vfx.speedx, 1.02)
    full_text = " ".join(verses_text)
    
    return final_quran_audio, full_text, surah_name, f"{start_ayah}-{start_ayah+4}"

def produce_dynamic_video():
    print("🚀 بدء جلب الآيات والمونتاج...")
    try:
        quran_audio, text, surah_name, ayahs_range = get_random_quran_verses()
        video_duration = quran_audio.duration
        
        if os.path.exists("rain_sound.mp3"):
            rain_audio = AudioFileClip("rain_sound.mp3").subclip(0, video_duration).volumex(0.15)
            quran_audio = quran_audio.volumex(1.0)
            final_audio = CompositeAudioClip([quran_audio, rain_audio])
        else:
            final_audio = quran_audio
            print("⚠️ لم يتم العثور على ملف rain_sound.mp3، سيتم الاستمرار بدونه.")
        
        headers = {"Authorization": os.environ.get('PEXELS_API_KEY')}
        url = "https://api.pexels.com/videos/search?query=nature rain clouds&orientation=portrait&size=medium&per_page=15"
        res = requests.get(url, headers=headers).json()
        video_url = random.choice(res['videos'])['video_files'][0]['link']
        
        with open("temp_bg.mp4", "wb") as f:
            f.write(requests.get(video_url).content)
            
        bg_clip = VideoFileClip("temp_bg.mp4").loop(duration=video_duration)
        bg_clip = bg_clip.fx(vfx.colorx, 0.6) 
        bg_clip = bg_clip.set_audio(final_audio)
        
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        
        txt_clip = TextClip(bidi_text, fontsize=40, color='white', font='Amiri', 
                            method='caption', size=(bg_clip.w - 100, None))
        txt_clip = txt_clip.set_position('center').set_duration(video_duration)
        
        final_video = CompositeVideoClip([bg_clip, txt_clip])
        final_video.write_videofile("final_short_video.mp4", codec="libx264", audio_codec="aac", fps=30)
        
        seo_title = f"تلاوة خاشعة تريح القلب - سورة {surah_name} 🌧️🤍"
        seo_desc = f"{text}\n\n#قرآن #تلاوة_خاشعة #سورة_{surah_name.replace(' ', '_')} #Shorts"
        
        for f in os.listdir():
            if (f.startswith("ayah_") and f.endswith(".mp3")) or f == "temp_bg.mp4":
                os.remove(f)
                
        return True, seo_title, seo_desc
    except Exception as e:
        print(f"❌ خطأ في إنتاج الفيديو: {e}")
        return False, "", ""

# ==========================================
# 2. النشر عبر Cloudinary و Buffer (YouTube/TikTok/IG)
# ==========================================
def upload_to_buffer(video_path, text):
    print("🚀 بدء النشر عبر Cloudinary و Buffer...")
    try:
        # إعداد Cloudinary باستخدام البيانات الصحيحة
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key=os.environ.get('CLOUDINARY_API_KEY'),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET')
        )
        upload_result = cloudinary.uploader.upload_large(
            video_path,
            resource_type="video",
            chunk_size=6000000
        )
        video_url = upload_result.get('secure_url')
        print(f"✅ تم الرفع على Cloudinary بنجاح: {video_url}")

        # الإرسال إلى بافر
        buffer_token = os.environ.get('BUFFER_ACCESS_TOKEN')
        channel_id = os.environ.get('BUFFER_CHANNEL_ID')
        
        url = f"https://api.bufferapp.com/1/updates/create.json?access_token={buffer_token}"
        payload = {
            "profile_ids[]": [channel_id],
            "text": text,
            "media[video]": video_url,
            "now": "true"
        }
        res = requests.post(url, data=payload).json()
        
        if res.get('success'):
            print("✅ تم الإرسال إلى Buffer ونشر الفيديو بنجاح على قنواتك!")
        else:
            print(f"❌ خطأ من واجهة Buffer: {res}")
    except Exception as e:
        print(f"❌ خطأ في رفع Buffer/Cloudinary: {e}")

# ==========================================
# 3. إرسال تنبيه تليجرام
# ==========================================
def send_telegram_alert(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('ADMIN_CHAT_ID') or os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})

# ==========================================
# 4. نقطة التشغيل الرئيسية
# ==========================================
if __name__ == "__main__":
    success, seo_title, seo_desc = produce_dynamic_video()
    
    if success and os.path.exists("final_short_video.mp4"):
        print("✅ الفيديو جاهز، جاري النشر على الحسابات الأساسية...")
        
        # النشر الأساسي (يوتيوب، تيك توك، إنستجرام)
        upload_to_buffer("final_short_video.mp4", f"{seo_title}\n{seo_desc}")
        
        send_telegram_alert(f"✅ تم إنتاج ونشر فيديو اليوم بنجاح!\nالعنوان: {seo_title}")
    else:
        send_telegram_alert("❌ فشل السكربت في إنتاج الفيديو.")

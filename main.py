import os
import time
import random
import requests
import tweepy
import cloudinary
import cloudinary.uploader
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, TextClip, CompositeVideoClip, concatenate_audioclips
import moviepy.video.fx.all as vfx
import arabic_reshaper
from bidi.algorithm import get_display

# ==========================================
# 1. محرك جلب القرآن وإنتاج الفيديو
# ==========================================
def get_random_quran_verses():
    # اختيار سورة عشوائية
    surah_num = random.randint(1, 114)
    surah_req = requests.get(f"http://api.alquran.cloud/v1/surah/{surah_num}").json()
    total_ayahs = surah_req['data']['numberOfAyahs']
    surah_name = surah_req['data']['name']
    
    # ضمان وجود 5 آيات متتالية
    start_ayah = random.randint(1, max(1, total_ayahs - 4))
    
    audio_clips = []
    verses_text = []
    
    # استخدام صوت المنشاوي (أو أي قارئ آخر لتجنب الحقوق)
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
    
    # تسريع الصوت بنسبة 2% لتخطي بصمة حقوق النشر (Content ID)
    final_quran_audio = final_quran_audio.fx(vfx.speedx, 1.02)
    full_text = " ".join(verses_text)
    
    return final_quran_audio, full_text, surah_name, f"{start_ayah}-{start_ayah+4}"

def produce_dynamic_video():
    print("🚀 بدء جلب الآيات والمونتاج...")
    try:
        quran_audio, text, surah_name, ayahs_range = get_random_quran_verses()
        video_duration = quran_audio.duration
        
        # دمج صوت المطر مع التلاوة
        if os.path.exists("rain_sound.mp3"):
            rain_audio = AudioFileClip("rain_sound.mp3").subclip(0, video_duration).volumex(0.15)
            quran_audio = quran_audio.volumex(1.0)
            final_audio = CompositeAudioClip([quran_audio, rain_audio])
        else:
            final_audio = quran_audio
            print("⚠️ لم يتم العثور على ملف rain_sound.mp3، سيتم الاستمرار بدونه.")
        
        # جلب فيديو طبيعة متحرك من Pexels
        headers = {"Authorization": os.environ.get('PEXELS_API_KEY')}
        url = "https://api.pexels.com/videos/search?query=nature rain clouds&orientation=portrait&size=medium&per_page=15"
        res = requests.get(url, headers=headers).json()
        video_url = random.choice(res['videos'])['video_files'][0]['link']
        
        with open("temp_bg.mp4", "wb") as f:
            f.write(requests.get(video_url).content)
            
        bg_clip = VideoFileClip("temp_bg.mp4").loop(duration=video_duration)
        # تعتيم خفيف للفيديو لكي يظهر النص بوضوح
        bg_clip = bg_clip.fx(vfx.colorx, 0.6) 
        bg_clip = bg_clip.set_audio(final_audio)
        
        # معالجة النص العربي
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        
        # تأكد من تحديد مسار خط يدعم العربية إذا تطلب الأمر، مثل 'Amiri'
        txt_clip = TextClip(bidi_text, fontsize=40, color='white', font='Amiri', 
                            method='caption', size=(bg_clip.w - 100, None))
        txt_clip = txt_clip.set_position('center').set_duration(video_duration)
        
        final_video = CompositeVideoClip([bg_clip, txt_clip])
        final_video.write_videofile("final_short_video.mp4", codec="libx264", audio_codec="aac", fps=30)
        
        seo_title = f"تلاوة خاشعة تريح القلب - سورة {surah_name} 🌧️🤍"
        seo_desc = f"{text}\n\n#قرآن #تلاوة_خاشعة #سورة_{surah_name.replace(' ', '_')} #Shorts"
        
        # تنظيف الملفات المؤقتة
        for f in os.listdir():
            if (f.startswith("ayah_") and f.endswith(".mp3")) or f == "temp_bg.mp4":
                os.remove(f)
                
        return True, seo_title, seo_desc
    except Exception as e:
        print(f"❌ خطأ في إنتاج الفيديو: {e}")
        return False, "", ""

# ==========================================
# 2. دوال الرفع للمنصات
# ==========================================
def upload_to_buffer(video_path, text):
    print("🚀 بدء النشر عبر Buffer...")
    try:
        cloudinary.config( 
          cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'), 
          api_key = os.environ.get('CLOUDINARY_API_KEY'), 
          api_secret = os.environ.get('CLOUDINARY_API_SECRET') 
        )
        upload_result = cloudinary.uploader.upload_large(video_path, resource_type="video")
        video_url = upload_result['secure_url']
        
        buffer_token = os.environ.get('BUFFER_ACCESS_TOKEN')
        buffer_profile = os.environ.get('BUFFER_CHANNEL_ID')
        
        headers = {"Authorization": f"Bearer {buffer_token}"}
        data = {"profile_ids[]": buffer_profile, "text": text, "media[video]": video_url}
        requests.post("https://api.bufferapp.com/1/updates/create.json", headers=headers, data=data)
        print("✅ تم الإرسال إلى Buffer بنجاح!")
    except Exception as e:
        print(f"❌ خطأ في Buffer: {e}")

def get_headless_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--mute-audio')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def upload_to_twitter(video_path, text):
    print("🚀 بدء الرفع على X (Twitter)...")
    try:
        auth = tweepy.OAuth1UserHandler(
            os.environ.get('X_API_KEY'), os.environ.get('X_API_SECRET'),
            os.environ.get('TWITTER_ACCESS_TOKEN'), os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(video_path)

        client = tweepy.Client(
            consumer_key=os.environ.get('X_API_KEY'), consumer_secret=os.environ.get('X_API_SECRET'),
            access_token=os.environ.get('TWITTER_ACCESS_TOKEN'), access_token_secret=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        )
        client.create_tweet(text=text, media_ids=[media.media_id])
        print("✅ تم النشر بنجاح على X!")
    except Exception as e:
        print(f"❌ خطأ في X: {e}")

def upload_to_dailymotion(video_path, title, description):
    print("🚀 بدء الرفع على Dailymotion...")
    try:
        auth_req = requests.post("https://api.dailymotion.com/oauth/token", data={
            "grant_type": "password",
            "client_id": os.environ.get('DM_API_KEY'),
            "client_secret": os.environ.get('DM_API_SECRET'),
            "username": os.environ.get('DM_USERNAME'),
            "password": os.environ.get('DM_PASSWORD')
        }).json()
        access_token = auth_req.get("access_token")

        upload_url = requests.get("https://api.dailymotion.com/file/upload", 
                                  headers={"Authorization": f"Bearer {access_token}"}).json().get("upload_url")
        with open(video_path, 'rb') as f:
            video_url = requests.post(upload_url, files={'file': f}).json().get("url")

        requests.post("https://api.dailymotion.com/me/videos", data={
            "url": video_url, "title": title, "description": description, "published": "true"
        }, headers={"Authorization": f"Bearer {access_token}"})
        print("✅ تم الرفع بنجاح على Dailymotion!")
    except Exception as e:
        print(f"❌ خطأ في Dailymotion: {e}")

def upload_to_febspot(video_path, title, description):
    print("🚀 بدء الرفع على Febspot...")
    driver = get_headless_driver()
    try:
        driver.get("https://www.febspot.com/login")
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(os.environ.get('FEBSPOT_EMAIL'))
        driver.find_element(By.NAME, "password").send_keys(os.environ.get('FEBSPOT_PASSWORD'))
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        time.sleep(5) 
        driver.get("https://www.febspot.com/my/upload")
        
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(os.path.abspath(video_path))
        
        title_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='title']")))
        title_input.clear()
        title_input.send_keys(title)
        
        desc_input = driver.find_element(By.XPATH, "//textarea[@name='description']")
        desc_input.clear()
        desc_input.send_keys(description)
        
        driver.find_element(By.XPATH, "//button[contains(text(), 'Publish')]").click()
        time.sleep(10)
        print("✅ تم الرفع بنجاح على Febspot!")
    except Exception as e:
        print(f"❌ خطأ في Febspot: {e}")
    finally:
        driver.quit()

def upload_to_costv(video_path, title):
    print("🚀 بدء الرفع على COS.TV...")
    driver = get_headless_driver()
    try:
        driver.get("https://cos.tv/v2/login")
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email']"))).send_keys(os.environ.get('COSTV_EMAIL'))
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys(os.environ.get('COSTV_PASSWORD'))
        driver.find_element(By.XPATH, "//button[contains(@class, 'login-btn')]").click()
        
        time.sleep(5)
        driver.get("https://cos.tv/studio/video/upload")
        
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(os.path.abspath(video_path))
        
        title_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'title-input')]")))
        title_input.clear()
        title_input.send_keys(title)
        
        driver.find_element(By.XPATH, "//button[contains(text(), 'Upload')]").click()
        time.sleep(15)
        print("✅ تم الرفع بنجاح على COS.TV!")
    except Exception as e:
        print(f"❌ خطأ في COS.TV: {e}")
    finally:
        driver.quit()

def send_telegram_alert(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('ADMIN_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})

# ==========================================
# 3. التشغيل الرئيسي
# ==========================================
if __name__ == "__main__":
    success, seo_title, seo_desc = produce_dynamic_video()
    
    if success and os.path.exists("final_short_video.mp4"):
        print("✅ جاري التوزيع على المنصات بالبيانات الديناميكية...")
        
        upload_to_buffer("final_short_video.mp4", f"{seo_title}\n{seo_desc}")
        upload_to_twitter("final_short_video.mp4", f"{seo_title}\n{seo_desc}")
        upload_to_dailymotion("final_short_video.mp4", seo_title, seo_desc)
        upload_to_febspot("final_short_video.mp4", seo_title, seo_desc)
        upload_to_costv("final_short_video.mp4", seo_title)
        
        send_telegram_alert(f"✅ تم النشر بنجاح!\nالعنوان: {seo_title}")
    else:
        send_telegram_alert("❌ فشل السكربت في إنتاج الفيديو.")

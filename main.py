import os
import time
import requests
import tweepy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. إعداد متصفح Selenium المخفي لبيئة GitHub
# ==========================================
def get_headless_driver():
    options = Options()
    options.add_argument('--headless') # التشغيل في الخلفية بدون واجهة
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--mute-audio')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# ==========================================
# 2. الرفع على Dailymotion (عبر API)
# ==========================================
def upload_to_dailymotion(video_path, title, description):
    print("🚀 بدء الرفع على Dailymotion...")
    api_key = os.environ.get('DM_API_KEY')
    api_secret = os.environ.get('DM_API_SECRET')
    username = os.environ.get('DM_USERNAME') # البريد الإلكتروني
    password = os.environ.get('DM_PASSWORD')

    try:
        # أ. الحصول على Access Token
        auth_url = "https://api.dailymotion.com/oauth/token"
        auth_data = {
            "grant_type": "password",
            "client_id": api_key,
            "client_secret": api_secret,
            "username": username,
            "password": password
        }
        auth_req = requests.post(auth_url, data=auth_data).json()
        access_token = auth_req.get("access_token")

        # ب. الحصول على رابط الرفع
        upload_url_req = requests.get("https://api.dailymotion.com/file/upload", 
                                      headers={"Authorization": f"Bearer {access_token}"}).json()
        upload_url = upload_url_req.get("upload_url")

        # ج. رفع ملف الفيديو
        with open(video_path, 'rb') as f:
            upload_res = requests.post(upload_url, files={'file': f}).json()
        video_url = upload_res.get("url")

        # د. نشر الفيديو وإضافة التفاصيل
        publish_url = "https://api.dailymotion.com/me/videos"
        publish_data = {
            "url": video_url,
            "title": title,
            "description": description,
            "published": "true"
        }
        requests.post(publish_url, data=publish_data, headers={"Authorization": f"Bearer {access_token}"})
        print("✅ تم الرفع بنجاح على Dailymotion!")
    except Exception as e:
        print(f"❌ خطأ في Dailymotion: {e}")

# ==========================================
# 3. الرفع على X / Twitter (عبر API)
# ==========================================
def upload_to_twitter(video_path, text):
    print("🚀 بدء الرفع على X (Twitter)...")
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

    try:
        # استخدام الإصدار 1.1 لرفع الميديا
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(video_path)

        # استخدام الإصدار 2 لكتابة التغريدة ونشرها
        client = tweepy.Client(
            consumer_key=api_key, consumer_secret=api_secret,
            access_token=access_token, access_token_secret=access_token_secret
        )
        client.create_tweet(text=text, media_ids=[media.media_id])
        print("✅ تم النشر بنجاح على X!")
    except Exception as e:
        print(f"❌ خطأ في X (Twitter): {e}")

# ==========================================
# 4. الرفع على Febspot (عبر Selenium)
# ==========================================
def upload_to_febspot(video_path, title, description):
    print("🚀 بدء الرفع على Febspot...")
    driver = get_headless_driver()
    try:
        driver.get("https://www.febspot.com/login")
        wait = WebDriverWait(driver, 15)
        
        # تسجيل الدخول
        # ملاحظة: استبدل مسارات الـ XPATH إذا تغير تصميم الموقع
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(os.environ.get('FEBSPOT_EMAIL'))
        driver.find_element(By.NAME, "password").send_keys(os.environ.get('FEBSPOT_PASSWORD'))
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # الانتقال لصفحة الرفع
        time.sleep(5) 
        driver.get("https://www.febspot.com/my/upload")
        
        # إرسال مسار الفيديو لزر الرفع
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(os.path.abspath(video_path))
        
        # كتابة العنوان والوصف
        title_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='title']")))
        title_input.clear()
        title_input.send_keys(title)
        
        desc_input = driver.find_element(By.XPATH, "//textarea[@name='description']")
        desc_input.clear()
        desc_input.send_keys(description)
        
        # الضغط على زر النشر النهائي
        driver.find_element(By.XPATH, "//button[contains(text(), 'Publish')]").click()
        time.sleep(10) # انتظار لضمان اكتمال الطلب
        print("✅ تم الرفع بنجاح على Febspot!")
    except Exception as e:
        print(f"❌ خطأ في Febspot: {e}")
    finally:
        driver.quit()

# ==========================================
# 5. الرفع على COS.TV (عبر Selenium)
# ==========================================
def upload_to_costv(video_path, title, description):
    print("🚀 بدء الرفع على COS.TV...")
    driver = get_headless_driver()
    try:
        driver.get("https://cos.tv/v2/login")
        wait = WebDriverWait(driver, 15)
        
        # تسجيل الدخول
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email']"))).send_keys(os.environ.get('COSTV_EMAIL'))
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys(os.environ.get('COSTV_PASSWORD'))
        driver.find_element(By.XPATH, "//button[contains(@class, 'login-btn')]").click()
        
        time.sleep(5)
        driver.get("https://cos.tv/studio/video/upload")
        
        # رفع الملف
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(os.path.abspath(video_path))
        
        # تعبئة البيانات (قد تحتاج لتعديل الـ XPATH بناءً على كود الموقع الفعلي)
        title_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'title-input')]")))
        title_input.clear()
        title_input.send_keys(title)
        
        # إرسال النموذج
        driver.find_element(By.XPATH, "//button[contains(text(), 'Upload')]").click()
        time.sleep(15)
        print("✅ تم الرفع بنجاح على COS.TV!")
    except Exception as e:
        print(f"❌ خطأ في COS.TV: {e}")
    finally:
        driver.quit()

# ==========================================
# 6. التشغيل الرئيسي
# ==========================================
if __name__ == "__main__":
    # مسار الفيديو المنتج من السكربت الخاص بك
    VIDEO_FILE = "final_short_video.mp4" 
    VIDEO_TITLE = "صلي على النبي وتابعني - معلومة سريعة"
    VIDEO_DESC = "ادعمنا بالمتابعة للمزيد من الفيديوهات القصيرة المفيدة يومياً."
    
    # التأكد من وجود الملف قبل الرفع
    if os.path.exists(VIDEO_FILE):
        print(f"تم العثور على الفيديو: {VIDEO_FILE}، جاري توزيعه على المنصات...")
        
        # يمكنك تفعيل أو تعطيل أي منصة بوضع علامة # قبلها
        upload_to_twitter(VIDEO_FILE, f"{VIDEO_TITLE}\n{VIDEO_DESC}")
        upload_to_dailymotion(VIDEO_FILE, VIDEO_TITLE, VIDEO_DESC)
        upload_to_febspot(VIDEO_FILE, VIDEO_TITLE, VIDEO_DESC)
        upload_to_costv(VIDEO_FILE, VIDEO_TITLE, VIDEO_DESC)
        
        print("🎉 اكتملت دورة النشر الأوتوماتيكية!")
    else:
        print("❌ ملف الفيديو غير موجود!")

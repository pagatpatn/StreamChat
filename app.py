import time
import requests
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os

# ================= USER CONFIG =================
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
KICK_CHANNEL_URL = os.getenv("KICK_CHANNEL_URL", "https://kick.com/lastmove")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
NTFY_DELAY = int(os.getenv("NTFY_DELAY", 2))
YOUTUBE_POLL_INTERVAL = 10  # seconds
KICK_POLL_INTERVAL = 5      # seconds
# ================================================

sent_messages = set()  # Track sent messages to avoid duplicates

# -------------------- NTFY --------------------
def send_ntfy_notification(title, message):
    try:
        requests.post(
            NTFY_TOPIC,
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "high"},
            timeout=5
        )
        time.sleep(NTFY_DELAY)
    except Exception as e:
        print("❌ Failed to send NTFY notification:", e)

# -------------------- YouTube --------------------
def get_youtube_live_chat_id():
    try:
        url = (
            f"https://www.googleapis.com/youtube/v3/search?part=snippet"
            f"&channelId={YOUTUBE_CHANNEL_ID}&eventType=live&type=video&key={YOUTUBE_API_KEY}"
        )
        resp = requests.get(url).json()
        items = resp.get("items", [])
        if not items:
            return None
        video_id = items[0]["id"]["videoId"]
        videos_url = (
            f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails"
            f"&id={video_id}&key={YOUTUBE_API_KEY}"
        )
        resp2 = requests.get(videos_url).json()
        return resp2["items"][0]["liveStreamingDetails"].get("activeLiveChatId")
    except Exception as e:
        print("❌ YouTube error:", e)
        return None

def youtube_chat_listener():
    page_token = None
    while True:
        live_chat_id = get_youtube_live_chat_id()
        if live_chat_id:
            print("🎥 YouTube is live!")
            while True:
                try:
                    url = f"https://www.googleapis.com/youtube/v3/liveChat/messages?liveChatId={live_chat_id}&part=snippet,authorDetails&key={YOUTUBE_API_KEY}"
                    if page_token:
                        url += f"&pageToken={page_token}"
                    resp = requests.get(url).json()
                    if "error" in resp:
                        break
                    for item in resp.get("items", []):
                        msg_id = item["id"]
                        if msg_id in sent_messages:
                            continue
                        sent_messages.add(msg_id)
                        user = item["authorDetails"]["displayName"]
                        msg = item["snippet"]["displayMessage"]
                        print(f"[YouTube] {user}: {msg}")
                        send_ntfy_notification(title=f"YouTube: {user}", message=msg)
                    page_token = resp.get("nextPageToken")
                    time.sleep(resp.get("pollingIntervalMillis", YOUTUBE_POLL_INTERVAL*1000)/1000)
                except Exception as e:
                    print("❌ YouTube polling error:", e)
                    time.sleep(YOUTUBE_POLL_INTERVAL)
        else:
            print("⏳ No YouTube live, retrying in 15s...")
            time.sleep(15)

# -------------------- Kick --------------------
def kick_browser_listener():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # Reduce memory usage
    driver = webdriver.Chrome(options=options)

    driver.get(KICK_CHANNEL_URL)
    time.sleep(5)

    try:
        live_badge = driver.find_element(By.XPATH, "//span[contains(text(),'LIVE')]")
        print("✅ Kick channel is live!")
    except:
        print("⏳ Kick is not live, will retry later")
        driver.quit()
        time.sleep(30)
        return

    last_seen_msgs = set()

    while True:
        try:
            chat_elements = driver.find_elements(By.CSS_SELECTOR, "div.chat-message")
            for chat_el in chat_elements:
                try:
                    msg_id = chat_el.get_attribute("id")
                    if msg_id in sent_messages or msg_id in last_seen_msgs:
                        continue
                    last_seen_msgs.add(msg_id)
                    sent_messages.add(msg_id)
                    username = chat_el.find_element(By.CSS_SELECTOR, "span.username").text
                    message = chat_el.find_element(By.CSS_SELECTOR, "span.message").text
                    print(f"[Kick] {username}: {message}")
                    send_ntfy_notification(title=f"Kick: {username}", message=message)
                except:
                    continue
            time.sleep(KICK_POLL_INTERVAL)
        except Exception as e:
            print("❌ Kick chat error:", e)
            time.sleep(KICK_POLL_INTERVAL)

# -------------------- MAIN --------------------
if __name__ == "__main__":
    yt_thread = threading.Thread(target=youtube_chat_listener, daemon=True)
    kick_thread = threading.Thread(target=kick_browser_listener, daemon=True)
    yt_thread.start()
    kick_thread.start()

    while True:
        time.sleep(60)

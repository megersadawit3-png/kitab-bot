import threading
import subprocess
import time

def run_main_bot():
    print("🟢 ዋናው ቦት እየተነሳ ነው...")
    subprocess.run(["python", "bot.py"])

def run_admin_bot():
    print("🔵 አድሚን ቦት እየተነሳ ነው...")
    subprocess.run(["python", "admin_bot.py"])

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 ሁለቱም ቦቶች እየተነሱ ነው...")
    print("=" * 50)
    
    t1 = threading.Thread(target=run_main_bot)
    t2 = threading.Thread(target=run_admin_bot)
    
    t1.daemon = True
    t2.daemon = True
    
    t1.start()
    t2.start()
    
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("\n⏹️ ቦቶቹ ተቋርጠዋል።")

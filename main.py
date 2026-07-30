import os
import re
import time
import json
import threading
import hashlib
import glob
import requests
import cloudscraper
from colorama import Fore, Style, init
from bs4 import BeautifulSoup

init(autoreset=True)

# ================= BANNER =================
def show_banner():
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
{Fore.CYAN}║                                                          ║
{Fore.GREEN}║     ███████╗██████╗  ██████╗ ██████╗  ██████╗ ████████╗
{Fore.GREEN}║     ██╔════╝██╔══██╗██╔════╝ ██╔══██╗██╔═══██╗╚══██╔══╝
{Fore.GREEN}║     █████╗  ██████╔╝██║  ███╗██████╔╝██║   ██║   ██║   
{Fore.GREEN}║     ██╔══╝  ██╔══██╗██║   ██║██╔══██╗██║   ██║   ██║   
{Fore.GREEN}║     ██║     ██████╔╝╚██████╔╝██║  ██║╚██████╔╝   ██║   
{Fore.GREEN}║     ╚═╝     ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   
{Fore.CYAN}║                                                          ║
{Fore.YELLOW}║        🔓 Facebook Forgot Password Tool (SMS Only)      ║
{Fore.CYAN}║                                                          ║
{Fore.MAGENTA}║     Developed by {Fore.WHITE}MR Chowdhury                      ║
{Fore.MAGENTA}║     Telegram: {Fore.WHITE}@Mrchowdhury100                     ║
{Fore.CYAN}║                                                          ║
{Fore.CYAN}╚══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
    print(banner)

# ================= CONFIG =================
with open("config.json") as f:
    config = json.load(f)

THREADS = config.get("threads", 3)
TIMEOUT = config.get("timeout", 10)
USE_PROXY = config.get("use_proxy", False)
PROXY_FILE = config.get("proxy_file", "proxies.txt")
ADMIN_ID = config.get("admin_id", "")

# ================= DEVICE APPROVAL =================
def get_device_id():
    info = os.popen("getprop ro.product.model 2>/dev/null || echo unknown").read().strip()
    info += os.popen("getprop ro.product.manufacturer 2>/dev/null || echo unknown").read().strip()
    info += os.popen("uname -a 2>/dev/null || echo unknown").read().strip()
    return hashlib.sha256(info.encode()).hexdigest()[:16]

def load_approved():
    if not os.path.exists("approved.json"):
        with open("approved.json", "w") as f:
            json.dump({"approved_devices": []}, f)
        return []
    with open("approved.json", "r") as f:
        data = json.load(f)
        return data.get("approved_devices", [])

def save_approved(devices):
    with open("approved.json", "w") as f:
        json.dump({"approved_devices": devices}, f, indent=4)

def is_approved(device_id):
    return device_id in load_approved()

def add_approved(device_id):
    devices = load_approved()
    if device_id not in devices:
        devices.append(device_id)
        save_approved(devices)
        return True
    return False

def remove_approved(device_id):
    devices = load_approved()
    if device_id in devices:
        devices.remove(device_id)
        save_approved(devices)
        return True
    return False

# ================= PROXY =================
def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

proxies = load_proxies()

# ================= CAPTCHA SOLVER =================
def solve_captcha(site_key, page_url):
    print(f"{Fore.YELLOW}[!] Captcha detected! Solving...")
    return "MANUAL_CAPTCHA_SOLVED"

# ================= FACEBOOK FORGOT (SMS ONLY) =================
def forgot_password_sms(phone, proxy=None):
    scraper = cloudscraper.create_scraper()
    
    if proxy:
        scraper.proxies = {"http": proxy, "https": proxy}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    url = "https://www.facebook.com/login/identify/"
    resp = session.get(url, timeout=TIMEOUT)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    form_data = {}
    for input_tag in soup.find_all("input"):
        name = input_tag.get("name")
        value = input_tag.get("value", "")
        if name:
            form_data[name] = value
    
    site_key = None
    for div in soup.find_all("div", {"data-sitekey": True}):
        site_key = div["data-sitekey"]
        break
    
    form_data["email"] = phone
    form_data["did_submit"] = "1"
    form_data["flow"] = "sms"
    
    if site_key:
        captcha_solution = solve_captcha(site_key, url)
        form_data["captcha"] = captcha_solution
    
    resp = session.post(url, data=form_data, timeout=TIMEOUT)
    
    if "checkpoint" in resp.url:
        return "✅ SMS sent"
    elif "confirm" in resp.url and "email" not in resp.url:
        return "✅ SMS sent"
    elif "recovery" in resp.url:
        return "✅ Recovery SMS available"
    elif "captcha" in resp.text.lower():
        return "❌ Captcha failed"
    elif "email" in resp.text.lower() and "sms" not in resp.text.lower():
        return "❌ Email only (SMS not available)"
    else:
        return "❌ Failed / Invalid"

# ================= LOAD NUMBERS FROM FOLDER =================
def load_numbers_from_folder(folder_path):
    numbers = set()
    
    if not os.path.exists(folder_path):
        print(f"{Fore.RED}❌ Folder not found: {folder_path}")
        return []
    
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    
    if not txt_files:
        print(f"{Fore.YELLOW}⚠️ No .txt files found in {folder_path}")
        return []
    
    print(f"{Fore.GREEN}[+] Found {len(txt_files)} .txt files")
    
    for file_path in txt_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    num = re.sub(r'\D', '', line.strip())
                    if len(num) >= 10:
                        numbers.add(num)
        except Exception as e:
            print(f"{Fore.RED}❌ Error reading {file_path}: {e}")
    
    return list(numbers)

# ================= WORKER =================
def worker(numbers, results, proxy_list, thread_id):
    for idx, number in enumerate(numbers):
        proxy = proxy_list[idx % len(proxy_list)] if proxy_list else None
        result = forgot_password_sms(number.strip(), proxy)
        results.append((number, result))
        print(f"{Fore.CYAN}[T{thread_id}] {number} → {result}")
        log_action(number, result)

def log_action(phone, status):
    with open("logs.txt", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {phone} | {status}\n")

# ================= ADMIN PANEL =================
def admin_panel():
    print(f"{Fore.YELLOW}━━━ Admin Panel ━━━")
    print("1. Show approved devices")
    print("2. Add device")
    print("3. Remove device")
    print("4. Back")
    choice = input("Select: ").strip()
    
    if choice == "1":
        devices = load_approved()
        print(f"{Fore.CYAN}Approved devices: {devices}")
        input("Press Enter to continue...")
    elif choice == "2":
        dev_id = input("Enter device ID to approve: ").strip()
        if add_approved(dev_id):
            print(f"{Fore.GREEN}✅ Device {dev_id} approved!")
        else:
            print(f"{Fore.RED}❌ Already approved or invalid.")
        input("Press Enter to continue...")
    elif choice == "3":
        dev_id = input("Enter device ID to remove: ").strip()
        if remove_approved(dev_id):
            print(f"{Fore.GREEN}✅ Device {dev_id} removed!")
        else:
            print(f"{Fore.RED}❌ Not found.")
        input("Press Enter to continue...")

# ================= MAIN =================
def main():
    show_banner()
    
    device_id = get_device_id()
    print(f"{Fore.CYAN}[Device ID] {device_id}")
    
    if not is_approved(device_id):
        print(f"{Fore.RED}❌ Device not approved!")
        print(f"{Fore.YELLOW}Contact admin to approve this device.")
        if device_id == ADMIN_ID:
            print(f"{Fore.GREEN}⚠️ You are admin. Do you want to approve yourself?")
            if input("Approve? (y/n): ").lower() == "y":
                add_approved(device_id)
                print(f"{Fore.GREEN}✅ Device approved!")
            else:
                return
        else:
            return
    
    print(f"{Fore.CYAN}📁 Enter folder path containing .txt files")
    print(f"{Fore.YELLOW}Example: /sdcard/numbers/ or /storage/emulated/0/numbers/")
    folder_path = input("Path: ").strip()
    
    if not folder_path:
        print(f"{Fore.RED}❌ No path provided!")
        return
    
    numbers = load_numbers_from_folder(folder_path)
    
    if not numbers:
        print(f"{Fore.RED}❌ No numbers found in {folder_path}")
        return
    
    print(f"{Fore.GREEN}[+] Loaded {len(numbers)} numbers")
    
    proxy_list = []
    if USE_PROXY and os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r") as f:
            proxy_list = [line.strip() for line in f if line.strip()]
        print(f"{Fore.GREEN}[+] Loaded {len(proxy_list)} proxies")
    
    chunk_size = max(1, len(numbers) // THREADS)
    chunks = [numbers[i:i+chunk_size] for i in range(0, len(numbers), chunk_size)]
    
    results = []
    threads = []
    
    for i, chunk in enumerate(chunks):
        t = threading.Thread(target=worker, args=(chunk, results, proxy_list, i+1))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    with open("report.txt", "w") as f:
        f.write("📊 Facebook Forgot Report (SMS Only)\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        f.write(f"Source Folder: {folder_path}\n")
        f.write(f"Total Numbers: {len(numbers)}\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
        for num, status in results:
            f.write(f"{num} → {status}\n")
    
    print(f"{Fore.GREEN}✅ Report saved to report.txt")
    
    if device_id == ADMIN_ID:
        if input("Open Admin Panel? (y/n): ").lower() == "y":
            admin_panel()

if __name__ == "__main__":
    main()

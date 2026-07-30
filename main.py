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

# ================= PROXY PARSER =================
def parse_proxy(proxy_str):
    proxy_str = proxy_str.strip()
    if not re.match(r'^[a-zA-Z]+://', proxy_str):
        proxy_str = 'http://' + proxy_str
    
    pattern = r'^(?P<protocol>https?|socks5)://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)$'
    match = re.match(pattern, proxy_str)
    
    if not match:
        return None
    
    data = match.groupdict()
    protocol = data['protocol']
    host = data['host']
    port = data['port']
    user = data.get('user')
    password = data.get('pass')
    
    if user and password:
        proxy_url = f"{protocol}://{user}:{password}@{host}:{port}"
    else:
        proxy_url = f"{protocol}://{host}:{port}"
    
    return {"http": proxy_url, "https": proxy_url}

# ================= PROXY INPUT =================
def get_proxy_list():
    print(f"{Fore.CYAN}🌐 Proxy Settings")
    print(f"{Fore.YELLOW}[1] Skip (no proxy)")
    print(f"{Fore.YELLOW}[2] Enter single proxy (host:port or user:pass@host:port)")
    print(f"{Fore.YELLOW}[3] Load from proxies.txt")
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
                        parsed = parse_proxy(line)
                        if parsed:
                            proxies.append(parsed)
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

# ================= FACEBOOK FORGOT =================
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
    resp = session.get(url, timeout=10)
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
    
    resp = session.post(url, data=form_data, timeout=10)
    
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

# ================= LOAD NUMBERS =================
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

# ================= MAIN =================
def main():
    show_banner()
    
    # ── Proxy ──
    proxy_list = get_proxy_list()
    if proxy_list:
        print(f"{Fore.GREEN}[+] Loaded {len(proxy_list)} proxies")
    else:
        print(f"{Fore.YELLOW}[!] No proxy used (direct connection)")
    
    # ── Folder Path ──
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
    
    # ── Threads ──
    try:
        threads_count = int(input(f"{Fore.CYAN}Enter threads (default 3): ").strip() or 3)
    except:
        threads_count = 3
    
    chunk_size = max(1, len(numbers) // threads_count)
    chunks = [numbers[i:i+chunk_size] for i in range(0, len(numbers), chunk_size)]
    
    results = []
    threads = []
    
    for i, chunk in enumerate(chunks):
        t = threading.Thread(target=worker, args=(chunk, results, proxy_list, i+1))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    # ── Report ──
    with open("report.txt", "w") as f:
        f.write("📊 Facebook Forgot Report (SMS Only)\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        f.write(f"Source Folder: {folder_path}\n")
        f.write(f"Total Numbers: {len(numbers)}\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
        for num, status in results:
            f.write(f"{num} → {status}\n")
    
    print(f"{Fore.GREEN}✅ Report saved to report.txt")

if __name__ == "__main__":
    main()

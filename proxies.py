import requests
import concurrent.futures

# Sumber proxy publik (format IP:PORT)
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

def ambil_proxies():
    proxies = []
    for url in PROXY_SOURCES:
        print(f"🔽 Mengambil dari: {url}")
        try:
            res = requests.get(url, timeout=10)
            lines = res.text.strip().splitlines()
            proxies += [line.strip() for line in lines if ":" in line]
            print(f"✅ {len(lines)} proxy ditemukan")
        except Exception as e:
            print(f"⚠️ Gagal mengambil: {e}")
    return list(set(proxies))

def cek_proxy(proxy):
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",  # pakai HTTP meskipun koneksi HTTPS
    }
    try:
        res = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=5)
        if res.status_code == 200:
            return proxy
    except:
        return None

def filter_proxy(proxies, max_ok=1000):
    print(f"🔎 Mengecek {len(proxies)} proxy...")
    valid = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(cek_proxy, proxy): proxy for proxy in proxies}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            result = future.result()
            if result:
                print(f"✅ VALID: {result}")
                valid.append(result)
            else:
                print(f"❌ Invalid ({i}/{len(proxies)})")
            if len(valid) >= max_ok:
                break
    return valid

def simpan_proxy(valid_proxies, filename="valid_proxies.txt"):
    with open(filename, "w") as f:
        for proxy in valid_proxies:
            f.write(f"https://{proxy}\n")
    print(f"📁 Disimpan: {len(valid_proxies)} proxy valid di '{filename}'.")

if __name__ == "__main__":
    all_proxies = ambil_proxies()
    valid = filter_proxy(all_proxies, max_ok=1000)
    simpan_proxy(valid)

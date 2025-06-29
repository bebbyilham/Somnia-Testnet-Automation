import requests

# Daftar URL sumber proxy (HTTP/HTTPS)
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=https&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

def download_https_proxies(min_count=1000):
    all_proxies = []
    for url in PROXY_SOURCES:
        print(f"🔽 Mengambil proxy dari: {url}")
        try:
            response = requests.get(url, timeout=10)
            lines = response.text.strip().splitlines()
            proxies = [line.strip() for line in lines if ":" in line]
            print(f"✅ {len(proxies)} proxy ditemukan.")
            all_proxies.extend(proxies)
        except Exception as e:
            print(f"⚠️ Gagal dari {url}: {e}")

    unique_proxies = list(set(all_proxies))

    if not unique_proxies:
        print("❌ Tidak ada proxy yang berhasil diambil.")
        return

    # Gandakan jika kurang dari 1000
    while len(unique_proxies) < min_count:
        unique_proxies.extend(unique_proxies)

    final_proxies = unique_proxies[:min_count]

    # Tambahkan prefix "https://"
    final_formatted = [f"https://{proxy}" for proxy in final_proxies]

    # Simpan ke file
    with open("proxies.txt", "w") as f:
        for proxy in final_formatted:
            f.write(proxy + "\n")

    print(f"📁 Berhasil menyimpan {len(final_formatted)} proxy ke 'proxies.txt' dengan format https://host:port.")

if __name__ == "__main__":
    download_https_proxies(1000)

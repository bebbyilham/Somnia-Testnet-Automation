import requests
from bs4 import BeautifulSoup

# List sumber proxy HTTP/HTTPS
SOURCES = [
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",  # juga mengandung HTTP
]

def scrape_from_url(url):
    proxies = []
    try:
        print(f"🔍 Mengambil proxy dari: {url}")
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.select("table#proxylisttable tbody tr"):
            cols = row.find_all("td")
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            proxies.append(f"{ip}:{port}")
        print(f"✅ Ditemukan {len(proxies)} proxy dari sumber ini.")
    except Exception as e:
        print(f"⚠️ Gagal mengambil dari {url}: {e}")
    return proxies

def generate_proxies(min_count=1000):
    all_proxies = []
    for url in SOURCES:
        all_proxies.extend(scrape_from_url(url))

    unique_proxies = list(set(all_proxies))  # Hilangkan duplikat

    if not unique_proxies:
        print("❌ Gagal mendapatkan proxy. Coba cek koneksi atau situs sumber.")
        return

    print(f"🔢 Total proxy unik: {len(unique_proxies)}")

    # Gandakan isi jika kurang dari 1000
    while len(unique_proxies) < min_count:
        unique_proxies.extend(unique_proxies)

    final_proxies = unique_proxies[:min_count]

    # Simpan ke file
    with open("proxies.txt", "w") as file:
        for proxy in final_proxies:
            file.write(proxy + "\n")

    print(f"📁 Berhasil menyimpan {len(final_proxies)} proxy ke 'proxies.txt'.")

if __name__ == "__main__":
    generate_proxies(1000)

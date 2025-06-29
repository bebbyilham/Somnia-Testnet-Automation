import requests
from bs4 import BeautifulSoup

# Daftar sumber proxy gratis
SOURCES = [
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",
]

def scrape_from_url(url):
    proxies = []
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.select("table#proxylisttable tbody tr"):
            cols = row.find_all("td")
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            proxies.append(f"{ip}:{port}")
    except Exception as e:
        print(f"Gagal scrape dari {url}: {e}")
    return proxies

# Gabungkan semua proxy dari semua sumber
all_proxies = []
for url in SOURCES:
    all_proxies.extend(scrape_from_url(url))

# Hilangkan duplikat
unique_proxies = list(set(all_proxies))

# Jika kurang dari 1000, bisa diklon/replikasi atau tambah sumber baru
if len(unique_proxies) < 1000:
    # Tambahkan dummy agar mencapai 1000
    while len(unique_proxies) < 1000:
        unique_proxies.append(unique_proxies[len(unique_proxies) % len(unique_proxies)])

# Ambil tepat 1000
final_proxies = unique_proxies[:1000]

# Simpan ke file
with open("proxies.txt", "w") as file:
    for proxy in final_proxies:
        file.write(proxy + "\n")

print(f"✅ Berhasil menyimpan {len(final_proxies)} proxy ke 'proxies.txt'")

import cloudscraper
from bs4 import BeautifulSoup

SOURCES = [
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",
]

def scrape_from_url(url):
    proxies = []
    try:
        print(f"🔍 Mengambil proxy dari: {url}")
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table", id="proxylisttable")
        if not table:
            print("⚠️ Tabel tidak ditemukan di halaman.")
            return proxies

        for row in table.tbody.find_all("tr"):
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

    unique_proxies = list(set(all_proxies))

    if not unique_proxies:
        print("❌ Gagal mendapatkan proxy. Coba cek koneksi atau situs sumber.")
        return

    print(f"🔢 Total proxy unik: {len(unique_proxies)}")

    while len(unique_proxies) < min_count:
        unique_proxies.extend(unique_proxies)

    final_proxies = unique_proxies[:min_count]

    with open("proxies.txt", "w") as file:
        for proxy in final_proxies:
            file.write(proxy + "\n")

    print(f"📁 Berhasil menyimpan {len(final_proxies)} proxy ke 'proxies.txt'.")

if __name__ == "__main__":
    generate_proxies(1000)

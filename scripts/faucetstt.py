import os
import sys
import random
import json
import time
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from colorama import init, Fore, Style
from web3 import Web3
import concurrent.futures

init(autoreset=True)

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(os.path.dirname(__file__), "..", "config.json"))
try:
    with open(CONFIG_PATH, "r") as f:
        config_data = json.load(f)
except Exception as e:
    print(f"{Fore.RED}  ✖ Error reading config.json: {str(e)}{Style.RESET_ALL}")
    sys.exit(1)
THREADS = config_data.get("threads", {}).get("maxWorkers", 10)

# Constants
FAUCET_API_URL = "https://testnet.somnia.network/api/faucet"
IP_CHECK_URL = "https://api.ipify.org?format=json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://testnet.somnia.network",
    "referer": "https://testnet.somnia.network/"
}

def print_border(text: str, color=Fore.CYAN, width=80):
    text = text.strip()
    if len(text) > width - 4:
        text = text[:width - 7] + "..."
    padded_text = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

def print_separator(color=Fore.MAGENTA):
    print(f"{color}{'═' * 80}{Style.RESET_ALL}")

def load_addresses(file_path: str = "addressFaucet.txt") -> list:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.RED} ✖ No addresses found in addressFaucet.txt{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add addresses here, one per line\n# e.g., 0x1234567890abcdef1234567890abcdef1234567890\n")
            return []
        addresses = []
        with open(file_path, 'r') as f:
            for line in f:
                addr = line.strip()
                if addr and not addr.startswith('#') and Web3.is_address(addr):
                    addresses.append(Web3.to_checksum_address(addr))
        if not addresses:
            print(f"{Fore.RED} ✖ No addresses found in addressFaucet.txt{Style.RESET_ALL}")
            return []
        print(f"{Fore.YELLOW} ℹ Found {len(addresses)} addresses in addressFaucet.txt{Style.RESET_ALL}")
        return addresses
    except Exception as e:
        print(f"{Fore.RED} ✖ Error: {str(e)}{Style.RESET_ALL}")
        return []

def load_proxies(file_path: str = "proxies.txt") -> list:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.YELLOW} ⚠ No proxies found in proxies.txt. None.{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add proxies here, one per line\n# e.g., socks5://user:pass@host:port or http://host:port\n")
            return []
        proxies = []
        with open(file_path, 'r') as f:
            for line in f:
                proxy = line.strip()
                if proxy and not proxy.startswith('#'):
                    proxies.append(proxy)
        if not proxies:
            print(f"{Fore.YELLOW} ⚠ No proxies found in proxies.txt. None.{Style.RESET_ALL}")
            return []
        print(f"{Fore.YELLOW} ℹ Found {len(proxies)} proxies in proxies.txt{Style.RESET_ALL}")
        return proxies
    except Exception as e:
        print(f"{Fore.RED} ✖ Error: {str(e)}{Style.RESET_ALL}")
        return []

async def get_proxy_ip(proxy: str = None) -> str:
    try:
        if proxy:
            if proxy.startswith(('socks5://', 'socks4://', 'http://', 'https://')):
                connector = ProxyConnector.from_url(proxy)
            else:
                parts = proxy.split(':')
                if len(parts) == 4:
                    proxy_url = f"socks5://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                    connector = ProxyConnector.from_url(proxy_url)
                elif len(parts) == 3 and '@' in proxy:
                    connector = ProxyConnector.from_url(f"socks5://{proxy}")
                else:
                    print(f"{Fore.YELLOW} ⚠ Invalid proxy: {proxy}{Style.RESET_ALL}")
                    return "Unknown"
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(IP_CHECK_URL, headers=HEADERS) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('ip', "Unknown")
                    return "Unknown"
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(IP_CHECK_URL, headers=HEADERS) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('ip', "Unknown")
                    return "Unknown"
    except Exception as e:
        print(f"{Fore.YELLOW} Error: {str(e)}{Style.RESET_ALL}")
        return "Unknown"

async def claim_faucet(address: str, proxy: str = None, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            if proxy:
                if proxy.startswith(('socks5://', 'socks4://', 'http://', 'https://')):
                    connector = ProxyConnector.from_url(proxy)
                else:
                    parts = proxy.split(':')
                    if len(parts) == 4:
                        proxy_url = f"socks5://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                        connector = ProxyConnector.from_url(proxy_url)
                    elif len(parts) == 3 and '@' in proxy:
                        connector = ProxyConnector.from_url(f"socks5://{proxy}")
                    else:
                        raise ValueError(f"Invalid proxy format: {proxy}")
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.post(FAUCET_API_URL, json={"address": address}, headers=HEADERS) as response:
                        data = await response.json()
                        if response.status == 200:
                            return data
                        elif response.status == 403:
                            raise Exception(403, "First register an account with Somnia")
                        elif "error" in data:
                            if "24 hours" in data["error"]:
                                raise Exception(response.status, "Please wait 24 hours between requests")
                            elif "Rate limit exceeded" in data["error"]:
                                raise Exception(response.status, "Rate limit exceeded")
                            else:
                                raise Exception(response.status, data.get("details", str(data)))
                        else:
                            raise Exception(response.status, await response.text())
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.post(FAUCET_API_URL, json={"address": address}, headers=HEADERS) as response:
                        data = await response.json()
                        if response.status == 200:
                            return data
                        elif response.status == 403:
                            raise Exception(403, "First register an account with Somnia")
                        elif "error" in data:
                            if "24 hours" in data["error"]:
                                raise Exception(response.status, "Please wait 24 hours between requests")
                            elif "Rate limit exceeded" in data["error"]:
                                raise Exception(response.status, "Rate limit exceeded")
                            else:
                                raise Exception(response.status, data.get("details", str(data)))
                        else:
                            raise Exception(response.status, await response.text())
        except Exception as e:
            code = e.args[0] if len(e.args) > 0 else "Unknown"
            response_text = e.args[1] if len(e.args) > 1 else str(e)
            if "try again" in response_text.lower() and attempt < max_retries - 1:
                delay = random.uniform(5, 15)
                print(f"{Fore.YELLOW} Retrying after {delay:.2f} seconds...{Style.RESET_ALL}")
                await asyncio.sleep(delay)
                continue
            raise Exception(code, response_text)

async def process_address(address: str, proxy: str = None):
    print(f"{Fore.CYAN} 🚀 Initializing Faucet for address - [{address}]{Style.RESET_ALL}")
    public_ip = await get_proxy_ip(proxy)
    proxy_display = proxy if proxy else "None"
    print(f"{Fore.CYAN} 🔄 Using Proxy - [{proxy_display}] with Public IP - [{public_ip}]{Style.RESET_ALL}")
    try:
        api_response = await claim_faucet(address, proxy)
        print(f"{Fore.GREEN} ✅ Faucet successfully claimed for address - [{address}]{Style.RESET_ALL}")
        print(f"{Fore.YELLOW} 🔗 API Response: {json.dumps(api_response)}{Style.RESET_ALL}")
    except Exception as e:
        code = e.args[0] if len(e.args) > 0 else "Unknown"
        response_text = e.args[1] if len(e.args) > 1 else str(e)
        if code == 403:
            print(f"{Fore.RED} ⚠️ Register an account with Somnia first, then request tokens{Style.RESET_ALL}")
        elif "24 hours" in response_text:
            print(f"{Fore.YELLOW} ⚠️ Please wait 24 hours between requests{Style.RESET_ALL}")
        elif "Rate limit" in response_text:
            print(f"{Fore.YELLOW} ⚠️ Rate limit exceeded, try again later{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED} ⚠️ Faucet request failed with code - [{code}] API Response: {response_text}{Style.RESET_ALL}")

def process_address_sync(address: str, proxy: str):
    try:
        asyncio.run(process_address(address, proxy))
        return True
    except Exception as e:
        print(f"{Fore.RED} Error: {str(e)}{Style.RESET_ALL}")
        return False

def run_faucetstt():
    print()
    print_border("SOMNIA TESTNET FAUCET", Fore.CYAN)
    print()
    addresses = load_addresses('addressFaucet.txt')
    if not addresses:
        return
    proxies = load_proxies('proxies.txt')
    print()
    total_addresses = len(addresses)
    successful = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for idx, address in enumerate(addresses, start=1):
            proxy = proxies[idx-1] if idx-1 < len(proxies) else None
            futures.append(executor.submit(process_address_sync, address, proxy))
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                successful += 1
    print_border("✅ Faucet claim completed!", Fore.GREEN)

if __name__ == "__main__":
    run_faucetstt()

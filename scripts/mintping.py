import os
import sys
import json
import random
import asyncio
from typing import List
from web3 import Web3
from colorama import init, Fore, Style
import concurrent.futures

init(autoreset=True)

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(os.path.dirname(__file__), "..", "config.json"))
try:
    with open(CONFIG_PATH, "r") as f:
        config_data = json.load(f)
except Exception as e:
    print(f"{Fore.RED}  ✖ Failed to read config.json: {str(e)}{Style.RESET_ALL}")
    sys.exit(1)

THREADS = config_data.get("threads", {}).get("maxWorkers", 10)
SHUFFLE_WALLETS = True
MINT_PONGPING_SLEEP_RANGE = [100, 300]

# Constants
SOMNIA_TESTNET_RPC_URL = 'https://dream-rpc.somnia.network'
SOMNIA_TESTNET_EXPLORER_URL = 'https://shannon-explorer.somnia.network'
CONTRACT_ADDRESS = "0x33E7fAB0a8a5da1A923180989bD617c9c2D1C493"

def print_border(text: str, color=Fore.CYAN, width=80):
    text = text.strip()
    if len(text) > width - 4:
        text = text[:width - 7] + "..."
    padded_text = f" {text} ".center(width - 2)
    print(f"\n{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}\n")

def is_valid_private_key(key: str) -> bool:
    key = key.strip()
    if not key.startswith('0x'):
        key = '0x' + key
    try:
        bytes.fromhex(key[2:])
        return len(key) == 66
    except ValueError:
        return False

def load_private_keys(file_path="pvkey.txt", language='en') -> List[str]:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.RED}  ✖ File pvkey.txt not found{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add private keys here...\n")
            sys.exit(1)
        keys = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                key = line.strip()
                if key and not key.startswith('#') and is_valid_private_key(key):
                    if not key.startswith('0x'):
                        key = '0x' + key
                    keys.append(key)
                elif key:
                    print(f"{Fore.YELLOW}  ⚠ Line {i} is invalid: {key}{Style.RESET_ALL}")
        if not keys:
            print(f"{Fore.RED}  ✖ No valid private keys found{Style.RESET_ALL}")
            sys.exit(1)
        return keys
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error reading pvkey.txt: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def connect_web3(language: str):
    try:
        w3 = Web3(Web3.HTTPProvider(SOMNIA_TESTNET_RPC_URL))
        if not w3.is_connected():
            print(f"{Fore.RED}  ✖ Could not connect to RPC{Style.RESET_ALL}")
            sys.exit(1)
        print(f"{Fore.GREEN}  ✔ Successfully connected to RPC │ Chain ID: {w3.eth.chain_id}{Style.RESET_ALL}")
        return w3
    except Exception as e:
        print(f"{Fore.RED}  ✖ Web3 connection error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def mint_ping_sync(private_key: str, wallet_index: int, language: str = 'en') -> bool:
    try:
        w3 = connect_web3(language)
        account = w3.eth.account.from_key(private_key)
        address = account.address
        balance = w3.eth.get_balance(address)

        print(f"{Fore.YELLOW}  ℹ Wallet {wallet_index}: {w3.from_wei(balance, 'ether'):.4f} STT{Style.RESET_ALL}")
        if balance < w3.to_wei(0.002, 'ether'):
            print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Insufficient STT to mint{Style.RESET_ALL}")
            return False

        # ABI قرارداد برای تابع mint بدون پارامتر
        abi = [
            {
                "inputs": [],
                "name": "mint",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

        # ساخت تراکنش
        nonce = w3.eth.get_transaction_count(address)
        min_gas_price = w3.to_wei('36', 'gwei')  # مشابه تراکنش دستی
        gas_price = max(int(w3.eth.gas_price * 1.5), min_gas_price)  # حاشیه برای شبکه شلوغ
        tx = contract.functions.mint().build_transaction({
            'from': address,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': w3.eth.chain_id,
        })

        # تنظیم گس لیمیت
        try:
            estimated_gas = w3.eth.estimate_gas(tx)
            tx['gas'] = min(int(estimated_gas * 1.5), 79124)  # حاشیه 50%، حداکثر 79124 مثل تراکنش دستی
        except Exception as gas_error:
            print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Gas estimation failed: {str(gas_error)}{Style.RESET_ALL}")
            tx['gas'] = 79124  # فال‌بک به گس لیمیت تراکنش دستی

        # لاگ اطلاعات تراکنش
        print(f"{Fore.YELLOW}  ℹ Wallet {wallet_index}: Gas Price: {w3.from_wei(gas_price, 'gwei')} Gwei, Gas Limit: {tx['gas']}, Data: {tx['data']}{Style.RESET_ALL}")

        # امضا و ارسال
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"{Fore.GREEN}  ✔ Wallet {wallet_index}: Transaction sent: {SOMNIA_TESTNET_EXPLORER_URL}/tx/0x{tx_hash.hex()}{Style.RESET_ALL}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

        if receipt.status == 1:
            print(f"{Fore.GREEN}  ✔ Wallet {wallet_index}: Mint successful{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Transaction failed. Check explorer for revert reason.{Style.RESET_ALL}")
            return False

    except Exception as e:
        print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Error processing: {str(e)}")
        if hasattr(e, 'args') and e.args:
            print(f"{Fore.RED}  Details: {e.args}{Style.RESET_ALL}")
        # لاگ اضافی برای دیباگ ری‌ورت
        if str(e).startswith("execution reverted"):
            print(f"{Fore.YELLOW}  ℹ Wallet {wallet_index}: Attempting to fetch revert reason...{Style.RESET_ALL}")
            try:
                w3.eth.call(tx, block_number='latest')
            except Exception as call_error:
                print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Revert reason: {str(call_error)}{Style.RESET_ALL}")
        return False

def run_mintping(language: str = 'en'):
    print_border("STARTING $PING MINT", Fore.CYAN)
    private_keys = load_private_keys(language=language)
    if SHUFFLE_WALLETS:
        random.shuffle(private_keys)

    print(f"{Fore.YELLOW}  ℹ Found {len(private_keys)} valid wallet(s){Style.RESET_ALL}\n")
    success = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for idx, pk in enumerate(private_keys, 1):
            futures.append(executor.submit(mint_ping_sync, pk, idx, language))
        for f in concurrent.futures.as_completed(futures):
            if f.result():
                success += 1

    print_border(f"COMPLETED: {success}/{len(private_keys)} wallets minted successfully", Fore.GREEN)

if __name__ == "__main__":
    run_mintping('en')
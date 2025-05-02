import os
import sys
import json
import random
import asyncio
import concurrent.futures

from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style

init(autoreset=True)

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(os.path.dirname(__file__), "..", "config.json"))
try:
    with open(CONFIG_PATH, "r") as f:
        config_data = json.load(f)
except Exception as e:
    print(f"{Fore.RED}  ✖ Error reading config.json: {str(e)}{Style.RESET_ALL}")
    sys.exit(1)

THREADS = config_data.get("threads", {}).get("maxWorkers", 10)

BORDER_WIDTH = 80

NETWORK_URL = "https://dream-rpc.somnia.network"
CHAIN_ID = 50312
EXPLORER_URL = "https://shannon-explorer.somnia.network/tx/0x"
CONTRACT_ADDRESS = "0x65296738D4E5edB1515e40287B6FDf8320E6eE04"
MINT_AMOUNT = 1000
MINT_DATA = "0x1249c58b"

def print_border(text: str, color=Fore.CYAN, width=BORDER_WIDTH):
    text = text.strip()
    if len(text) > width - 4:
        text = text[:width - 7] + "..."
    padded_text = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

def print_separator(color=Fore.MAGENTA):
    print(f"{color}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")

def is_valid_private_key(key: str) -> bool:
    key = key.strip()
    if not key.startswith('0x'):
        key = '0x' + key
    try:
        bytes.fromhex(key.replace('0x', ''))
        return len(key) == 66
    except ValueError:
        return False

def load_private_keys(file_path: str = "pvkey.txt") -> list:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.RED}  ✖ pvkey.txt file not found{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add private keys here, one per line\n# 0x1234...\n")
            sys.exit(1)

        valid_keys = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                key = line.strip()
                if key and not key.startswith('#'):
                    if is_valid_private_key(key):
                        if not key.startswith('0x'):
                            key = '0x' + key
                        valid_keys.append((i, key))
                    else:
                        print(f"{Fore.YELLOW}  ⚠ Warning: Line {i} is invalid: {key}{Style.RESET_ALL}")

        if not valid_keys:
            print(f"{Fore.RED}  ✖ No valid private keys found{Style.RESET_ALL}")
            sys.exit(1)

        return valid_keys
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed to read pvkey.txt: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def connect_web3():
    try:
        w3 = Web3(Web3.HTTPProvider(NETWORK_URL))
        if not w3.is_connected():
            print(f"{Fore.RED}  ✖ Failed to connect to RPC{Style.RESET_ALL}")
            sys.exit(1)
        print(f"{Fore.GREEN}  ✔ Success: Connected to Somnia Testnet │ Chain ID: {w3.eth.chain_id}{Style.RESET_ALL}")
        return w3
    except Exception as e:
        print(f"{Fore.RED}  ✖ Web3 connection failed: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def has_minted_susdt(w3: Web3, address: str) -> bool:
    susdt_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=susdt_abi)
    try:
        balance = contract.functions.balanceOf(address).call()
        return balance > 0
    except Exception as e:
        print(f"{Fore.YELLOW}  ⚠ Failed to check sUSDT balance: {str(e)}{Style.RESET_ALL}")
        return False

async def mint_susdt(w3: Web3, private_key: str, wallet_index: int):
    account = Account.from_key(private_key)
    sender_address = account.address

    if has_minted_susdt(w3, sender_address):
        print(f"{Fore.YELLOW}  ⚠ This wallet has already minted sUSDT! Skipping this request.{Style.RESET_ALL}")
        return False

    try:
        print(f"{Fore.CYAN}  > Checking balance...{Style.RESET_ALL}")
        balance = float(w3.from_wei(w3.eth.get_balance(sender_address), 'ether'))
        if balance < 0.001:
            print(f"{Fore.RED}  ✖ Insufficient balance: {balance:.4f} STT < 0.001 STT{Style.RESET_ALL}")
            return False

        print(f"{Fore.CYAN}  > Preparing transaction...{Style.RESET_ALL}")
        nonce = w3.eth.get_transaction_count(sender_address)
        tx_params = {
            'nonce': nonce,
            'to': Web3.to_checksum_address(CONTRACT_ADDRESS),
            'value': 0,
            'data': MINT_DATA,
            'chainId': CHAIN_ID,
            'gas': 200000,
            'gasPrice': int(w3.eth.gas_price * random.uniform(1.03, 1.1))
        }

        print(f"{Fore.CYAN}  > Sending transaction...{Style.RESET_ALL}")
        signed_tx = w3.eth.account.sign_transaction(tx_params, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_link = f"{EXPLORER_URL}{tx_hash.hex()}"

        receipt = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180))
        if receipt.status == 1:
            print(f"{Fore.GREEN}  ✔ Successfully minted 1000 sUSDT! │ Tx: {tx_link}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}  ✖ Mint failed │ Tx: {tx_link}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed: {str(e)}{Style.RESET_ALL}")
        return False

def mint_susdt_sync(w3: Web3, private_key: str, wallet_index: int) -> bool:
    return asyncio.run(mint_susdt(w3, private_key, wallet_index))

def run_mintsusdt():
    print()
    print_border("MINT sUSDT - SOMNIA TESTNET", Fore.CYAN)
    print()

    private_keys = load_private_keys('pvkey.txt')
    print(f"{Fore.YELLOW}  ℹ Info: Found {len(private_keys)} wallets{Style.RESET_ALL}")
    print()
    if not private_keys:
        return

    w3 = connect_web3()
    print()

    successful_mints = 0
    total_wallets = len(private_keys)

    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for i, (line_num, privkey) in enumerate(private_keys, start=1):
            futures.append(executor.submit(mint_susdt_sync, w3, privkey, i))
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                successful_mints += 1

    print_border(f"COMPLETED: {successful_mints}/{total_wallets} TRANSACTIONS SUCCESSFUL", Fore.GREEN)
    print(f"{Fore.CYAN}Developed by Ostad kachal | GitHub: https://github.com/sinak1023}{Style.RESET_ALL}")

if __name__ == "__main__":
    run_mintsusdt()
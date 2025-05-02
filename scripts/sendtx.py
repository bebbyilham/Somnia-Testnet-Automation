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

DEV_WALLETS = [
    "0xDA1feA7873338F34C6915A44028aA4D9aBA1346B",
    "0x018604C67a7423c03dE3057a49709aaD1D178B85",
    "0xcF8D30A5Ee0D9d5ad1D7087822bA5Bab1081FdB7",
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5"
]

def print_border(text: str, color=Fore.CYAN, width=80):
    text = text.strip()
    if len(text) > width - 4:
        text = text[:width - 7] + "..."
    padded_text = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")
    print()

def print_separator(color=Fore.MAGENTA):
    print(f"{color}{'═' * 80}{Style.RESET_ALL}")

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
                f.write("# Add private keys here...\n")
            sys.exit(1)
        valid = []
        with open(file_path, 'r') as f:
            for line in f:
                key = line.strip()
                if key and not key.startswith('#'):
                    if is_valid_private_key(key):
                        if not key.startswith('0x'):
                            key = '0x' + key
                        valid.append(key)
        if not valid:
            print(f"{Fore.RED}  ✖ No valid private keys found{Style.RESET_ALL}")
            sys.exit(1)
        return valid
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed to read pvkey.txt: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def load_addresses(file_path: str = "address.txt") -> list:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.RED}  ✖ address.txt file not found{Style.RESET_ALL}")
            return None
        addresses = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                addr = line.strip()
                if addr:
                    try:
                        addresses.append(Web3.to_checksum_address(addr))
                    except:
                        print(f"{Fore.YELLOW}  ⚠ Warning: Line {i} is not a valid address: {addr}{Style.RESET_ALL}")
        if not addresses:
            print(f"{Fore.RED}  ✖ No valid addresses found in address.txt{Style.RESET_ALL}")
            return None
        return addresses
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed to read address.txt: {str(e)}{Style.RESET_ALL}")
        return None

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

async def send_transaction(w3: Web3, private_key: str, to_address: str, amount: float):
    account = Account.from_key(private_key)
    sender_address = account.address
    try:
        nonce = w3.eth.get_transaction_count(sender_address)
        latest_block = w3.eth.get_block('latest')
        base_fee_per_gas = latest_block.get('baseFeePerGas', w3.to_wei(2, 'gwei'))
        max_priority_fee_per_gas = w3.to_wei(2, 'gwei')
        max_fee_per_gas = base_fee_per_gas + max_priority_fee_per_gas

        tx = {
            'nonce': nonce,
            'to': w3.to_checksum_address(to_address),
            'value': w3.to_wei(amount, 'ether'),
            'gas': 21000,
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee_per_gas,
            'chainId': CHAIN_ID
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_link = f"{EXPLORER_URL}{tx_hash.hex()}"

        receipt = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180))
        if receipt.status == 1:
            print(f"{Fore.GREEN}  ✔ Transaction successful! │ Tx: {tx_link}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}  ✖ Transaction failed │ Tx: {tx_link}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed: {str(e)}{Style.RESET_ALL}")
        return False

def send_transaction_sync(w3: Web3, private_key: str, to_address: str, amount: float) -> bool:
    return asyncio.run(send_transaction(w3, private_key, to_address, amount))

def get_tx_count() -> int:
    print_border("ENTER NUMBER OF TRANSACTIONS", Fore.YELLOW)
    while True:
        tx_count_input = input(f"{Fore.YELLOW}  > Number of transactions (default 1): {Style.RESET_ALL}")
        if tx_count_input.strip() == '':
            tx_count_input = '1'
        try:
            tx_count = int(tx_count_input)
            if tx_count <= 0:
                print(f"{Fore.RED}  ✖ Error: Number of transactions must be greater than 0{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}  ✔ Selected: {tx_count} transactions{Style.RESET_ALL}")
                return tx_count
        except ValueError:
            print(f"{Fore.RED}  ✖ Error: Please enter a valid number{Style.RESET_ALL}")

def get_amount() -> float:
    print_border("ENTER AMOUNT OF STT", Fore.YELLOW)
    while True:
        amount_input = input(f"{Fore.YELLOW}  > Amount of STT (default 0.000001, max 999): {Style.RESET_ALL}")
        if amount_input.strip() == '':
            amount_input = '0.000001'
        try:
            amount = float(amount_input)
            if 0 < amount <= 999:
                print(f"{Fore.GREEN}  ✔ Selected: {amount} STT{Style.RESET_ALL}")
                return amount
            print(f"{Fore.RED}  ✖ Error: Amount must be greater than 0 and not exceed 999{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}  ✖ Error: Please enter a valid number{Style.RESET_ALL}")

def send_random_tx(w3: Web3, private_key: str, wallet_index: int, tx_count: int, amount: float) -> int:
    success = 0
    for tx_idx in range(1, tx_count + 1):
        to_addr = random.choice(DEV_WALLETS)
        if send_transaction_sync(w3, private_key, to_addr, amount):
            success += 1
    return success

def send_file_tx(w3: Web3, private_key: str, wallet_index: int, addresses: list, amount: float) -> int:
    success = 0
    for i, addr in enumerate(addresses, 1):
        if send_transaction_sync(w3, private_key, addr, amount):
            success += 1
    return success

def run_sendtx():
    print()
    print_border("SEND TX - SOMNIA TESTNET", Fore.CYAN)
    print()

    private_keys = load_private_keys()
    print(f"{Fore.YELLOW}  ℹ Info: Found {len(private_keys)} wallets{Style.RESET_ALL}")
    print()
    if not private_keys:
        return

    tx_count = get_tx_count()
    amount = get_amount()
    print_separator()

    w3 = connect_web3()
    print()

    while True:
        print_border("SELECT TRANSACTION TYPE", Fore.YELLOW)
        print(f"{Fore.CYAN}  1. Send to random SOMNIA DEV address{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  2. Send to addresses from file (address.txt){Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}  > Enter choice (1/2): {Style.RESET_ALL}")

        total_txs = 0
        successful = 0

        if choice == '1':
            print_border(f"STARTING {tx_count} RANDOM TRANSACTIONS", Fore.CYAN)
            print()
            total_txs = tx_count * len(private_keys)
            with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
                futures = []
                for idx, pk in enumerate(private_keys, 1):
                    futures.append(executor.submit(send_random_tx, w3, pk, idx, tx_count, amount))
                for f in concurrent.futures.as_completed(futures):
                    successful += f.result()
            break

        elif choice == '2':
            addresses = load_addresses('address.txt')
            if not addresses:
                return
            print_border(f"STARTING TRANSACTIONS TO {len(addresses)} ADDRESSES FROM FILE", Fore.CYAN)
            print()
            total_txs = len(private_keys) * len(addresses)
            with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
                futures = []
                for idx, pk in enumerate(private_keys, 1):
                    futures.append(executor.submit(send_file_tx, w3, pk, idx, addresses, amount))
                for f in concurrent.futures.as_completed(futures):
                    successful += f.result()
            break

        else:
            print(f"{Fore.RED}  ✖ Invalid choice{Style.RESET_ALL}")
            continue

    print()
    print_border(f"COMPLETED: {successful}/{total_txs} TRANSACTIONS SUCCESSFUL", Fore.GREEN)

if __name__ == "__main__":
    run_sendtx()

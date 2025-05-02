import os
import sys
import json
import random
import asyncio
import concurrent.futures
from typing import List

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
SOMNIA_TESTNET_RPC_URL = 'https://dream-rpc.somnia.network'
SOMNIA_TESTNET_EXPLORER_URL = 'https://shannon-explorer.somnia.network'
SHUFFLE_WALLETS = True

TOKEN_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

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

def load_private_keys(file_path: str = "pvkey.txt") -> List[str]:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.RED}  ✖ Error: pvkey.txt file not found{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add private keys here...\n")
            sys.exit(1)

        valid_keys = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                key = line.strip()
                if key and not key.startswith('#'):
                    if is_valid_private_key(key):
                        if not key.startswith('0x'):
                            key = '0x' + key
                        valid_keys.append(key)
                    else:
                        print(f"{Fore.YELLOW}  ⚠ Warning: line {i} is invalid, skipped: {key}{Style.RESET_ALL}")

        if not valid_keys:
            print(f"{Fore.RED}  ✖ Error: No valid private keys found{Style.RESET_ALL}")
            sys.exit(1)

        return valid_keys
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error: Failed to read pvkey.txt: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def shuffle_wallets(keys: List[str]) -> List[str]:
    return random.sample(keys, len(keys))

def connect_web3():
    try:
        w3 = Web3(Web3.HTTPProvider(SOMNIA_TESTNET_RPC_URL))
        if not w3.is_connected():
            print(f"{Fore.RED}  ✖ Error: Failed to connect to RPC{Style.RESET_ALL}")
            sys.exit(1)
        print(f"{Fore.GREEN}  ✔ Success: Connected to Somnia Testnet │ Chain ID: {w3.eth.chain_id}{Style.RESET_ALL}")
        return w3
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error: Web3 connection failed: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def get_swap_amount() -> float:
    print_border("ENTER $PING AMOUNT")

    while True:
        input_txt = input(f"{Fore.YELLOW}  > Amount of $PING to swap (e.g., 10): {Style.RESET_ALL}")
        try:
            amount = float(input_txt)
            if amount <= 0:
                print(f"{Fore.RED}  ✖ Error: Amount must be > 0{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}  ✔ Selected: {amount} $PING{Style.RESET_ALL}")
                return amount
        except ValueError:
            print(f"{Fore.RED}  ✖ Error: Please enter a valid number{Style.RESET_ALL}")

def get_swap_times() -> int:
    print_border("ENTER NUMBER OF SWAPS")

    while True:
        input_txt = input(f"{Fore.YELLOW}  > Number of swaps (default 1): {Style.RESET_ALL}")
        if input_txt.strip() == "":
            print(f"{Fore.GREEN}  ✔ Default selected: 1{Style.RESET_ALL}")
            return 1
        try:
            times = int(input_txt)
            if times <= 0:
                print(f"{Fore.RED}  ✖ Error: must be > 0{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}  ✔ Selected: {times}{Style.RESET_ALL}")
                return times
        except ValueError:
            print(f"{Fore.RED}  ✖ Error: Must be a valid integer{Style.RESET_ALL}")

async def approve_token(web3: Web3, private_key: str, token_address: str, spender_address: str,
                       amount: float, wallet_index: int) -> bool:
    try:
        account = Account.from_key(private_key)
        contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=TOKEN_ABI)
        decimals = contract.functions.decimals().call()
        amount_wei = int(amount * 10**decimals)

        tx = contract.functions.approve(
            Web3.to_checksum_address(spender_address),
            amount_wei
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': web3.eth.gas_price
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:
            print(f"{Fore.GREEN}  ✔ Wallet {wallet_index} Approved {amount} $PING: {SOMNIA_TESTNET_EXPLORER_URL}/tx/0x{tx_hash.hex()}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Approve failed{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Approve error: {e}{Style.RESET_ALL}")
        return False

async def swap_token(web3: Web3, private_key: str, token_in: str, token_out: str,
                     amount_in: float, recipient: str, wallet_index: int) -> bool:
    try:
        account = Account.from_key(private_key)
        swap_router_address = "0x6aac14f090a35eea150705f72d90e4cdc4a49b2c"
        fee = 500
        amount_out_min = int(amount_in * 0.97 * 10**18)
        amount_in_wei = int(amount_in * 10**18)

        SWAP_ROUTER_ABI = [
            {
                "inputs": [
                    {
                        "components": [
                            {"name": "tokenIn", "type": "address"},
                            {"name": "tokenOut", "type": "address"},
                            {"name": "fee", "type": "uint24"},
                            {"name": "recipient", "type": "address"},
                            {"name": "amountIn", "type": "uint256"},
                            {"name": "amountOutMinimum", "type": "uint256"},
                            {"name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"name": "amountOut", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        swap_router = web3.eth.contract(address=Web3.to_checksum_address(swap_router_address), abi=SWAP_ROUTER_ABI)

        tx_data = swap_router.functions.exactInputSingle(
            (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                fee,
                recipient,
                amount_in_wei,
                amount_out_min,
                0
            )
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': web3.eth.gas_price,
            'chainId': web3.eth.chain_id
        })
        signed_tx = web3.eth.account.sign_transaction(tx_data, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            print(f"{Fore.GREEN}  ✔ Wallet {wallet_index} Swapped {amount_in} $PING -> $PONG: {SOMNIA_TESTNET_EXPLORER_URL}/tx/0x{tx_hash.hex()}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Swap failed{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}  ✖ Wallet {wallet_index}: Swap error: {e}{Style.RESET_ALL}")
        return False

async def process_one_wallet(web3: Web3, private_key: str, wallet_index: int,
                             amount: float, swap_times: int) -> int:
    token_in = "0x33E7fAB0a8a5da1A923180989bD617c9c2D1C493"  # $PING
    token_out = "0x9beaA0016c22B646Ac311Ab171270B0ECf23098F"  # $PONG
    spender = "0x6aac14f090a35eea150705f72d90e4cdc4a49b2c"
    account = Account.from_key(private_key)
    recipient = account.address

    success_count = 0
    # Approve
    total_approve = amount * swap_times
    ok_approve = await approve_token(web3, private_key, token_in, spender, total_approve, wallet_index)
    if not ok_approve:
        return 0

    # swap
    for i in range(1, swap_times + 1):
        print(f"{Fore.CYAN}  > Swap {i}/{swap_times}{Style.RESET_ALL}")
        if await swap_token(web3, private_key, token_in, token_out, amount, recipient, wallet_index):
            success_count += 1
        print()
    return success_count

def process_one_wallet_sync(web3: Web3, private_key: str, wallet_index: int,
                            amount: float, swap_times: int) -> int:
    return asyncio.run(process_one_wallet(web3, private_key, wallet_index, amount, swap_times))

def run_swapping():
    print()
    print_border("START SWAPPING $PING -> $PONG")
    print()

    private_keys = load_private_keys()
    if SHUFFLE_WALLETS:
        private_keys = shuffle_wallets(private_keys)
    print(f"{Fore.YELLOW}  ℹ Found {len(private_keys)} wallets{Style.RESET_ALL}")
    print()
    if not private_keys:
        print(f"{Fore.RED}  ✖ No wallets to swap{Style.RESET_ALL}")
        return

    amount = get_swap_amount()
    swap_times = get_swap_times()
    print_separator()

    w3 = connect_web3()
    print()

    successful_swaps = 0
    total_swaps = len(private_keys) * swap_times

    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for idx, pk in enumerate(private_keys, 1):
            futures.append(
                executor.submit(process_one_wallet_sync, w3, pk, idx, amount, swap_times)
            )
        for f in concurrent.futures.as_completed(futures):
            successful_swaps += f.result()

    print_border(f"COMPLETED: {successful_swaps}/{total_swaps} SWAPS SUCCESSFUL", Fore.GREEN)

if __name__ == "__main__":
    run_swapping()

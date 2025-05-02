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

# Constants
NETWORK_URL = "https://dream-rpc.somnia.network"
CHAIN_ID = 50312
EXPLORER_URL = "https://shannon-explorer.somnia.network"

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "name_", "type": "string"},
            {"internalType": "string", "name": "symbol_", "type": "string"},
            {"internalType": "uint8", "name": "decimals_", "type": "uint8"},
            {"internalType": "uint256", "name": "totalSupply_", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "spender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"}
        ],
        "name": "Approval",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "transferFrom",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenOwner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "sendToken",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
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
    print()

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
        
        valid_keys = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                key = line.strip()
                if key and not key.startswith('#') and is_valid_private_key(key):
                    if not key.startswith('0x'):
                        key = '0x' + key
                    valid_keys.append((i, key))
        if not valid_keys:
            print(f"{Fore.RED}  ✖ No valid private keys found{Style.RESET_ALL}")
            sys.exit(1)
        return valid_keys
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed to read pvkey.txt: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def load_addresses(file_path: str = "addressERC20.txt") -> list:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.YELLOW}  ⚠ No addresses found in addressERC20.txt. Creating new file.{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add token recipient addresses here...\n")
            return []
        
        addresses = []
        with open(file_path, 'r') as f:
            for line in f:
                addr = line.strip()
                if addr and not addr.startswith('#') and Web3.is_address(addr):
                    addresses.append(Web3.to_checksum_address(addr))
        if not addresses:
            print(f"{Fore.YELLOW}  ⚠ No addresses found in addressERC20.txt{Style.RESET_ALL}")
        return addresses
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error: {str(e)}{Style.RESET_ALL}")
        return []

def connect_web3():
    try:
        w3 = Web3(Web3.HTTPProvider(NETWORK_URL))
        if not w3.is_connected():
            print(f"{Fore.RED}  ✖ Failed to connect to RPC{Style.RESET_ALL}")
            sys.exit(1)
        print(f"{Fore.GREEN}  ✔ Success: Connected to Somnia Testnet │ Chain ID: {w3.eth.chain_id}{Style.RESET_ALL}")
        return w3
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

async def send_token(w3: Web3, private_key: str, wallet_index: int, contract_address: str, destination: str, amount: float) -> bool:
    account = Account.from_key(private_key)
    sender_address = account.address
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=CONTRACT_ABI)
        decimals = contract.functions.decimals().call()
        amount_wei = int(amount * 10 ** decimals)

        print(f"{Fore.CYAN}  > Preparing transaction...{Style.RESET_ALL}")
        nonce = w3.eth.get_transaction_count(sender_address)

        tx = contract.functions.sendToken(Web3.to_checksum_address(destination), amount_wei).build_transaction({
            'from': sender_address,
            'nonce': nonce,
            'chainId': CHAIN_ID,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })

        print(f"{Fore.CYAN}  > Sending transaction...{Style.RESET_ALL}")
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_link = f"{EXPLORER_URL}/tx/0x{tx_hash.hex()}"

        receipt = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180))
        if receipt.status == 1:
            print(f"{Fore.GREEN}  ✔ Token sent successfully! │ Tx: {tx_link}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Wallet address: {sender_address}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Destination address: {destination}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Amount: {amount:.4f} Token{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Gas: {receipt['gasUsed']}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Block: {receipt['blockNumber']}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}  ✖ Token sending failed │ Tx: {tx_link}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed: {str(e)}{Style.RESET_ALL}")
        return False

def send_token_sync(w3: Web3, private_key: str, wallet_index: int, contract_address: str, destination: str, amount: float) -> bool:
    return asyncio.run(send_token(w3, private_key, wallet_index, contract_address, destination, amount))

def run_sendtoken():
    print()
    print_border("SEND ERC20 TOKEN - SOMNIA TESTNET", Fore.CYAN)
    print()

    private_keys = load_private_keys()
    print(f"{Fore.YELLOW}  ℹ Info: Found {len(private_keys)} wallets{Style.RESET_ALL}")
    print()
    if not private_keys:
        return

    w3 = connect_web3()
    print()

    print(f"{Fore.YELLOW}  ➤ Enter ERC20 contract address (contractERC20.txt): {Style.RESET_ALL}", end="")
    contract_address = input().strip()
    print(f"{Fore.YELLOW}  ➤ Enter token amount to send: {Style.RESET_ALL}", end="")
    amount_input = input().strip()

    try:
        amount = float(amount_input)
        if amount <= 0:
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}  ✖ Error: Please enter a valid number{Style.RESET_ALL}")
        return

    print()
    print(f"{Fore.CYAN}  ✦ Choose token sending method:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}    ├─ 1. Send randomly{Style.RESET_ALL}")
    print(f"{Fore.GREEN}    └─ 2. Send from addressERC20.txt{Style.RESET_ALL}")
    print()
    print(f"{Fore.YELLOW}  ➤ Enter your choice (1 or 2): {Style.RESET_ALL}", end="")
    choice = input().strip()

    destinations = []
    if choice == '1':
        destinations = []
        for _ in range(len(private_keys)):
            new_account = Web3(Web3.HTTPProvider(NETWORK_URL)).eth.account.create()
            destinations.append(new_account.address)
    elif choice == '2':
        addresses = load_addresses('addressERC20.txt')
        if not addresses:
            return
        destinations = addresses
    else:
        print(f"{Fore.RED}  ✖ Invalid choice{Style.RESET_ALL}")
        return

    successful_sends = 0
    total_wallets = len(private_keys)

    random.shuffle(private_keys)

    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for i, (line_num, privkey) in enumerate(private_keys, 1):
            if i-1 < len(destinations):
                dest = destinations[i-1]
            else:
                dest = random.choice(destinations)

            futures.append(
                executor.submit(send_token_sync, w3, privkey, i, contract_address, dest, amount)
            )

        for future in concurrent.futures.as_completed(futures):
            if future.result():
                successful_sends += 1

    print()
    print_border(f"COMPLETED: {successful_sends}/{total_wallets} TRANSACTIONS SUCCESSFUL", Fore.GREEN)

if __name__ == "__main__":
    run_sendtoken()

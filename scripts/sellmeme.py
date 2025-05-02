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
ROUTER_ADDRESS = "0x6aac14f090a35eea150705f72d90e4cdc4a49b2c"
SPENDER_ADDRESS = "0x6aac14f090a35eea150705f72d90e4cdc4a49b2c"
SUSDT_ADDRESS = "0x65296738D4E5edB1515e40287B6FDf8320E6eE04"
TOKENS = {
    "SOMI": {"address": "0x7a7045415f3682C3349E4b68d2940204b81fFF33", "price": 0.99960},
    "SMSM": {"address": "0x6756B4542d545270CacF1F15C3b7DefE589Ba1aa", "price": 0.99959},
    "SMI":  {"address": "0xC9005DD5C562bDdEF1Cf3C90Ad5B1Bf54fB8aa9d", "price": 0.99959},
    "sUSDT":{"address": "0x65296738D4E5edB1515e40287B6FDf8320E6eE04", "price": 1.0}
}

TOKEN_ABI = [
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

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

def print_border(text: str, color=Fore.CYAN, width=BORDER_WIDTH):
    text = f" {text} "
    padded_text = text.center(width - 2, "─")
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")
    print()

def print_separator(color=Fore.MAGENTA):
    print(f"{color}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
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
        print(f"{Fore.RED}  ✖ Error: {str(e)}{Style.RESET_ALL}")
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
        print(f"{Fore.RED}  ✖ Error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def get_token_info(w3: Web3, token_symbol: str, wallet_address: str):
    contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]["address"]), abi=TOKEN_ABI)
    try:
        balance = contract.functions.balanceOf(wallet_address).call() / 10**contract.functions.decimals().call()
        price = TOKENS[token_symbol]["price"]
        print(f"{Fore.YELLOW}    Balance       : {balance:,.2f} {token_symbol}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    Price         : {price:,.5f} sUSDT/{token_symbol}{Style.RESET_ALL}")
        if token_symbol != "sUSDT":
            total_supply = contract.functions.totalSupply().call() / 10**contract.functions.decimals().call()
            market_cap = price * total_supply
            print(f"{Fore.YELLOW}    Market Cap   : {market_cap:,.2f} sUSDT{Style.RESET_ALL}")
        print()
        return balance
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error: {str(e)}{Style.RESET_ALL}")
        return 0

def select_token():
    print_border("SELECT TOKEN TO SELL", Fore.YELLOW)
    print(f"{Fore.CYAN}  1. Somini (SOMI){Style.RESET_ALL}")
    print(f"{Fore.CYAN}  2. Somsom (SMSM){Style.RESET_ALL}")
    print(f"{Fore.CYAN}  3. Somi (SMI){Style.RESET_ALL}")
    print()
    while True:
        choice = input(f"{Fore.YELLOW}  > Select token to sell (1: SOMI │ 2: SMSM │ 3: SMI): {Style.RESET_ALL}")
        if choice == "1":
            return "SOMI"
        elif choice == "2":
            return "SMSM"
        elif choice == "3":
            return "SMI"
        else:
            print(f"{Fore.RED}  ✖ Invalid selection{Style.RESET_ALL}")

def get_amount(token_symbol: str):
    while True:
        try:
            amount = float(input(f"{Fore.YELLOW}  > Enter {token_symbol} amount to sell: {Style.RESET_ALL}"))
            if amount <= 0:
                print(f"{Fore.RED}  ✖ Error: Amount must be greater than 0{Style.RESET_ALL}")
            else:
                return amount
        except ValueError:
            print(f"{Fore.RED}  ✖ Error: Invalid number{Style.RESET_ALL}")

async def approve_token(w3: Web3, private_key: str, token_address: str, spender_address: str, amount: float, token_symbol: str):
    account = Account.from_key(private_key)
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=TOKEN_ABI)
    decimals = token_contract.functions.decimals().call()
    amount_wei = int(amount * (10 ** decimals))

    tx = token_contract.functions.approve(
        Web3.to_checksum_address(spender_address),
        amount_wei
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status == 1:
        print(f"{Fore.GREEN}  ✔ Successfully approved {amount:,.2f} {token_symbol}!{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}  ✖ Approve failed{Style.RESET_ALL}")
        return False

async def sell_token(w3: Web3, private_key: str, token_symbol: str, amount: float):
    account = Account.from_key(private_key)
    token_in = TOKENS[token_symbol]["address"]
    token_out = SUSDT_ADDRESS
    swap_router = w3.eth.contract(address=Web3.to_checksum_address(ROUTER_ADDRESS), abi=SWAP_ROUTER_ABI)

    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_in), abi=TOKEN_ABI)
    decimals = token_contract.functions.decimals().call()
    amount_in_wei = int(amount * (10 ** decimals))
    amount_out_minimum = int(amount * 0.95 * (10 ** decimals))

    tx_data = swap_router.functions.exactInputSingle(
        (
            Web3.to_checksum_address(token_in),
            Web3.to_checksum_address(token_out),
            500,
            account.address,
            amount_in_wei,
            amount_out_minimum,
            0
        )
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'chainId': CHAIN_ID
    })
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_link = f"{EXPLORER_URL}{tx_hash.hex()}"
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status == 1:
        print(f"{Fore.GREEN}  ✔ Successfully sold {amount:,.2f} {token_symbol} for sUSDT │ Tx: {tx_link}{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}  ✖ Sell failed │ Tx: {tx_link}{Style.RESET_ALL}")
        return False

async def handle_sell(w3: Web3, private_key: str, token_symbol: str, amount: float) -> bool:
    account = Account.from_key(private_key)
    token_balance = get_token_info(w3, token_symbol, account.address)
    if token_balance < amount:
        print(f"{Fore.RED}  ✖ Insufficient {token_symbol} balance: {token_balance:,.2f} < {amount:,.2f}{Style.RESET_ALL}")
        return False
    
    get_token_info(w3, "sUSDT", account.address)
    if not await approve_token(w3, private_key, TOKENS[token_symbol]['address'], SPENDER_ADDRESS, amount, token_symbol):
        return False
    
    return await sell_token(w3, private_key, token_symbol, amount)

def handle_sell_sync(w3: Web3, private_key: str, token_symbol: str, amount: float) -> bool:
    return asyncio.run(handle_sell(w3, private_key, token_symbol, amount))

def run_sellmeme():
    print()
    print_border("SELL MEME TOKEN - SOMNIA TESTNET", Fore.CYAN)

    private_keys = load_private_keys('pvkey.txt')
    print(f"{Fore.YELLOW}  ℹ Info: Found {len(private_keys)} wallets{Style.RESET_ALL}")
    print()
    if not private_keys:
        return

    w3 = connect_web3()
    print()

    token_symbol = select_token()
    amount = get_amount(token_symbol)
    print_separator()

    successful_sells = 0
    total_wallets = len(private_keys)

    random.shuffle(private_keys)

    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for i, (profile_num, privkey) in enumerate(private_keys, 1):
            futures.append(executor.submit(handle_sell_sync, w3, privkey, token_symbol, amount))
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                successful_sells += 1

    print()
    print_border(f"COMPLETED: {successful_sells}/{total_wallets} TRANSACTIONS SUCCESSFUL", Fore.GREEN)
    print(f"{Fore.CYAN}Developed by Ostad kachal | GitHub: https://github.com/sinak1023}{Style.RESET_ALL}")

if __name__ == "__main__":
    run_sellmeme()
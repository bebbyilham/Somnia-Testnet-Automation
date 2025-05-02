import os
import sys
import json
import random
import time
import concurrent.futures
import asyncio

from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc, get_solc_version
from colorama import init, Fore, Style

init(autoreset=True)

BORDER_WIDTH = 80

# Constants
NETWORK_URL = "https://dream-rpc.somnia.network"
CHAIN_ID = 50312
EXPLORER_URL = "https://shannon-explorer.somnia.network"
SOLC_VERSION = "0.8.22"

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(os.path.dirname(__file__), "..", "config.json"))
try:
    with open(CONFIG_PATH, "r") as f:
        config_data = json.load(f)
except Exception as e:
    print(f"{Fore.RED}  ✖ Error reading config.json: {str(e)}{Style.RESET_ALL}")
    sys.exit(1)
THREADS = config_data.get("threads", {}).get("maxWorkers", 10)

CONTRACT_SOURCE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

contract CustomToken {
    string private _name;
    string private _symbol;
    uint8 private _decimals;
    uint256 private _totalSupply;
    address public owner;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    constructor(
        string memory name_,
        string memory symbol_,
        uint8 decimals_,
        uint256 totalSupply_
    ) {
        owner = msg.sender;
        _name = name_;
        _symbol = symbol_;
        _decimals = decimals_;
        _totalSupply = totalSupply_;
        _balances[address(this)] = totalSupply_;
        emit Transfer(address(0), address(this), totalSupply_);
    }

    function name() public view returns (string memory) {
        return _name;
    }

    function symbol() public view returns (string memory) {
        return _symbol;
    }

    function decimals() public view returns (uint8) {
        return _decimals;
    }

    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function allowance(address tokenOwner, address spender) public view returns (uint256) {
        return _allowances[tokenOwner][spender];
    }

    function approve(address spender, uint256 amount) public returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= amount, "ERC20: transfer amount exceeds allowance");
        _transfer(from, to, amount);
        _approve(from, msg.sender, currentAllowance - amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "ERC20: transfer from the zero address");
        require(to != address(0), "ERC20: transfer to the zero address");
        require(_balances[from] >= amount, "ERC20: transfer amount exceeds balance");
        _balances[from] -= amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }

    function _approve(address tokenOwner, address spender, uint256 amount) internal {
        require(tokenOwner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");
        _allowances[tokenOwner][spender] = amount;
        emit Approval(tokenOwner, spender, amount);
    }

    function sendToken(address recipient, uint256 amount) external onlyOwner {
        _transfer(address(this), recipient, amount);
    }
}
"""

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
                f.write("# Add your private keys here, one per line\n# e.g., 0x1234567890abcdef...\n")
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

def ensure_solc_installed():
    try:
        current_version = get_solc_version()
        if str(current_version) != SOLC_VERSION:
            raise Exception("Solc version mismatch")
    except Exception:
        print(f"{Fore.YELLOW}  ℹ Installing solc version {SOLC_VERSION}...{Style.RESET_ALL}")
        install_solc(SOLC_VERSION)
        print(f"{Fore.GREEN}  ✔ Installed solc version {SOLC_VERSION}{Style.RESET_ALL}")

def compile_contract():
    ensure_solc_installed()
    compiled_sol = compile_source(CONTRACT_SOURCE, output_values=['abi', 'bin'], solc_version=SOLC_VERSION)
    contract_id, contract_interface = compiled_sol.popitem()
    return contract_interface['abi'], contract_interface['bin']

async def deploy_contract(w3: Web3, private_key: str, wallet_index: int, name: str, symbol: str, decimals: int, total_supply: int):
    account = Account.from_key(private_key)
    sender_address = account.address
    try:
        abi, bytecode = compile_contract()
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        print(f"{Fore.CYAN}  > Preparing transaction...{Style.RESET_ALL}")
        nonce = w3.eth.get_transaction_count(sender_address)
        total_supply_wei = w3.to_wei(total_supply, 'ether')
        tx = contract.constructor(name, symbol, decimals, total_supply_wei).build_transaction({
            'from': sender_address,
            'nonce': nonce,
            'chainId': CHAIN_ID,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        print(f"{Fore.CYAN}  > Sending transaction...{Style.RESET_ALL}\n")
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_link = f"{EXPLORER_URL}/tx/0x{tx_hash.hex()}"
        loop = asyncio.get_event_loop()
        receipt = await loop.run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180))
        if receipt.status == 1:
            contract_address = receipt.get('contractAddress')
            print(f"{Fore.GREEN}  ✔ Deployment successful! │ Tx: {tx_link}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Contract address: {contract_address}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Gas: {receipt.get('gasUsed')}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}    Block: {receipt.get('blockNumber')}{Style.RESET_ALL}")
            return contract_address
        else:
            print(f"{Fore.RED}  ✖ Deployment failed │ Tx: {tx_link}{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}  ✖ Failed: {str(e)}{Style.RESET_ALL}")
        return None

def process_one_wallet_sync(w3: Web3, wallet_index: int, total_wallets: int, profile_num: int, private_key: str,
                            name: str, symbol: str, decimals: int, total_supply: int):
    try:
        print_border(f"PROCESSING WALLET {profile_num} ({wallet_index}/{total_wallets})", Fore.MAGENTA)
        contract_address = asyncio.run(deploy_contract(w3, private_key, wallet_index, name, symbol, decimals, total_supply))
        if contract_address:
            with open('contractERC20.txt', 'a') as f:
                f.write(f"{contract_address}\n")
            result = True
        else:
            result = False
        if wallet_index < total_wallets:
            delay = random.uniform(10, 30)
            print(f"{Fore.YELLOW}  ℹ Pausing {delay:.2f} seconds{Style.RESET_ALL}")
            time.sleep(delay)
        print_separator()
        return result
    except Exception as e:
        print(f"{Fore.RED}  ✖ Error: {str(e)}{Style.RESET_ALL}")
        print_separator()
        return False

def run_deploytoken():
    print()
    print_border("DEPLOY ERC20 TOKEN - SOMNIA TESTNET", Fore.CYAN)
    print()
    private_keys = load_private_keys('pvkey.txt')
    print(f"{Fore.YELLOW}  ℹ Info: Found {len(private_keys)} wallets{Style.RESET_ALL}")
    print()
    if not private_keys:
        return
    w3 = connect_web3()
    print()
    name = input(f"{Fore.YELLOW}  > Enter token name (e.g., RPC Token): {Style.RESET_ALL}").strip()
    symbol = input(f"{Fore.YELLOW}  > Enter token symbol (e.g., RPC): {Style.RESET_ALL}").strip()
    decimals_input = input(f"{Fore.YELLOW}  > Enter decimals (default 18): {Style.RESET_ALL}").strip() or "18"
    total_supply_input = input(f"{Fore.YELLOW}  > Enter total supply (e.g., 1000000): {Style.RESET_ALL}").strip()
    try:
        decimals = int(decimals_input)
        total_supply = int(total_supply_input)
        if decimals <= 0 or total_supply <= 0:
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}  ✖ Please enter a valid number{Style.RESET_ALL}")
        return

    total_wallets = len(private_keys)
    random.shuffle(private_keys)
    successful_deploys = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for idx, (profile_num, pkey) in enumerate(private_keys, start=1):
            futures.append(
                executor.submit(
                    process_one_wallet_sync,
                    w3, idx, total_wallets, profile_num, pkey,
                    name, symbol, decimals, total_supply
                )
            )
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                successful_deploys += 1

    print()
    print_border(f"COMPLETED: {successful_deploys}/{total_wallets} TRANSACTIONS SUCCESSFUL", Fore.GREEN)
    print(f"{Fore.CYAN}Developed by Ostad kachal | GitHub: https://github.com/sinak1023}{Style.RESET_ALL}")

if __name__ == "__main__":
    run_deploytoken()
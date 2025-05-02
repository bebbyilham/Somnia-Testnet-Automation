import os
import sys
import asyncio
from colorama import init, Fore, Style
import inquirer
from banner import display_banner

init(autoreset=True)

BORDER_WIDTH = 80

def print_border(text: str, color=Fore.CYAN, width=BORDER_WIDTH):
    text = text.strip()
    if len(text) > width - 4:
        text = text[:width - 7] + "..."
    padded_text = f" {text} ".center(width - 2)
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│{padded_text}│{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

def _clear():
    os.system('cls' if os.name == 'nt' else 'clear')

async def run_faucetstt():
    from scripts.faucetstt import run_faucetstt as faucetstt_run
    faucetstt_run()

async def run_sendtx():
    from scripts.sendtx import run_sendtx as sendtx_run
    sendtx_run()

async def run_deploytoken():
    from scripts.deploytoken import run_deploytoken as deploytoken_run
    deploytoken_run()

async def run_sendtoken():
    from scripts.sendtoken import run_sendtoken as sendtoken_run
    sendtoken_run()

async def run_mintpong():
    from scripts.mintpong import run_mintpong as mintpong_run
    mintpong_run()

async def run_mintping():
    from scripts.mintping import run_mintping as mintping_run
    mintping_run()

async def run_swappong():
    from scripts.swappong import run_swappong as swappong_run
    swappong_run()

async def run_swapping():
    from scripts.swapping import run_swapping as swapping_run
    swapping_run()

async def run_conftnft():
    from scripts.conftnft import run_conftnft as conftnft_run
    conftnft_run()

async def run_mintsusdt():
    from scripts.mintsusdt import run_mintsusdt as mintsusdt_run
    mintsusdt_run()

async def run_buymeme():
    from scripts.buymeme import run_buymeme as buymeme_run
    buymeme_run()

async def run_sellmeme():
    from scripts.sellmeme import run_sellmeme as sellmeme_run
    sellmeme_run()

async def cmd_exit():
    print_border("Exiting...", Fore.GREEN)
    sys.exit(0)

SCRIPT_MAP = {
    "faucetstt": run_faucetstt,
    "sendtx": run_sendtx,
    "deploytoken": run_deploytoken,
    "sendtoken": run_sendtoken,
    "mintpong": run_mintpong,
    "mintping": run_mintping,
    "swappong": run_swappong,
    "swapping": run_swapping,
    "conftnft": run_conftnft,
    "mintsusdt": run_mintsusdt,
    "buymeme": run_buymeme,
    "sellmeme": run_sellmeme,
    "exit": cmd_exit
}

def get_available_scripts():
    scripts = [
        {"name": "1. Faucet token $STT", "value": "faucetstt"},
        {"name": "2. Mint $PONG | Somnia Testnet", "value": "mintpong"},
        {"name": "3. Mint $PING | Somnia Testnet", "value": "mintping"},
        {"name": "4. Send Random TX or File (address.txt) | Somnia Testnet", "value": "sendtx"},
        {"name": "5. Deploy Token smart-contract | Somnia Testnet", "value": "deploytoken"},
        {"name": "6. Send Token ERC20 Random or File (addressERC20.txt) | Somnia Testnet", "value": "sendtoken"},
        {"name": "7. Swap $PONG -> $PING | Somnia Testnet", "value": "swappong"},
        {"name": "8. Swap $PING -> $PONG | Somnia Testnet", "value": "swapping", "separator": True},
        {"name": "9. Mint NFT Community Member of Somnia (CMS - CoNFT) | Somnia Testnet", "value": "conftnft"},
        {"name": "10. Mint 1000 sUSDT | Somnia Testnet", "value": "mintsusdt"},
        {"name": "11. Memecoin Trading - Buy Memecoin ( SOMI / SMSM / SMI ) | Somnia Testnet", "value": "buymeme"},
        {"name": "12. Memecoin Trading - Sell Memecoin ( SOMI / SMSM / SMI ) | Somnia Testnet", "value": "sellmeme"},
        {"name": "13. Exit", "value": "exit"},
    ]
    return scripts

def run_script(script_func):
    if asyncio.iscoroutinefunction(script_func):
        asyncio.run(script_func())
    else:
        script_func()

def main():
    _clear()
    display_banner()
    while True:
        _clear()
        display_banner()
        print_border("MAIN MENU", Fore.YELLOW)

        available_scripts = get_available_scripts()
        questions = [
            inquirer.List('script',
                          message=f"{Fore.CYAN}Select script to run{Style.RESET_ALL}",
                          choices=[script["name"] for script in available_scripts],
                          carousel=True)
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            continue

        selected_script_name = answers['script']
        selected_script_value = next(script["value"] for script in available_scripts if script["name"] == selected_script_name)

        script_func = SCRIPT_MAP.get(selected_script_value)
        if script_func is None:
            print(f"{Fore.RED}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
            print_border(f"Not implemented: {selected_script_name}", Fore.RED)
            input(f"{Fore.YELLOW}⏎ Press Enter to continue...{Style.RESET_ALL:^76}")
            continue

        try:
            print(f"{Fore.CYAN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
            print_border(f"RUNNING: {selected_script_name}", Fore.CYAN)
            run_script(script_func)
            print(f"{Fore.GREEN}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
            print_border(f"Completed {selected_script_name}", Fore.GREEN)
            input(f"{Fore.YELLOW}⏎ Press Enter to continue...{Style.RESET_ALL:^76}")
        except Exception as e:
            print(f"{Fore.RED}{'═' * BORDER_WIDTH}{Style.RESET_ALL}")
            print_border(f"Error: {str(e)}", Fore.RED)
            input(f"{Fore.YELLOW}⏎ Press Enter to continue...{Style.RESET_ALL:^76}")

if __name__ == "__main__":
    main()
    print(f"{Fore.CYAN}Developed by Ostad kachal | GitHub: https://github.com/sinak1023}{Style.RESET_ALL}")
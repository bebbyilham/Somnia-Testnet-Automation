import os
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

def center_text(text, width=None):
    if width is None:
        width = os.get_terminal_size().columns
    return text.center(width)

def display_banner():
    width = os.get_terminal_size().columns  

    banner_text = f"""
{Fore.YELLOW}{center_text("SOMNIA TESTNET AUTOMATION 📝", width)}{Style.RESET_ALL}
{center_text(Fore.RED + "📢 GitHub: https://github.com/sinak1023" + Style.RESET_ALL, width)}

{Fore.YELLOW}{center_text("════════════════════════════════════════════════════════", width)}{Style.RESET_ALL}
{center_text(f"Started at: {Fore.WHITE}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}", width)}
{Fore.YELLOW}{center_text("════════════════════════════════════════════════════════", width)}{Style.RESET_ALL}
"""

    print(banner_text)
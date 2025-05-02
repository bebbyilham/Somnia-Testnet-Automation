# Somnia Testnet Automation Scripts

## Overview
This repository contains a collection of Python scripts designed to automate various tasks on the Somnia Testnet, including token minting, swapping, faucet claiming, and more. These scripts leverage the `web3.py` library to interact with the Somnia blockchain and are intended for developers and enthusiasts participating in the Somnia Testnet.

## Features
- **Token Minting**: Scripts to mint tokens like $PING, $PONG, and sUSDT.
- **Token Swapping**: Automate $PONG to $PING and $PING to $PONG swaps.
- **Faucet Claiming**: Claim testnet $STT tokens via the Somnia faucet API.
- **Token Deployment**: Deploy custom ERC20 tokens on the Somnia Testnet.
- **NFT Minting**: Mint Community Member of Somnia (CMS - CoNFT) NFTs.
- **Meme Token Trading**: Buy and sell meme tokens (SOMI, SMSM, SMI).
- **Transaction Sending**: Send random or file-based transactions.

## Prerequisites
- **Python 3.8+**

  ```
- **Files**:
  - `pvkey.txt`: Add private keys (one per line) for wallets.
  - `addressFaucet.txt`: Add wallet addresses for faucet claims.
  - `addressERC20.txt`: Add recipient addresses for token transfers.
  - `proxies.txt`: Add proxy addresses (optional, for faucet claims).
  - `contractERC20.txt`: Stores deployed ERC20 contract addresses (auto-generated).
- **Somnia Testnet RPC**: Ensure access to `https://dream-rpc.somnia.network`.
- **Somnia Testnet Explorer**: View transactions at `https://shannon-explorer.somnia.network`.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/sinak1023/Somnia-Testnet-Automation.git
   cd Somnia-Testnet-Automation
   ```
2. Install dependencies:
   ```bash
   pip install web3 eth-account colorama aiohttp aiohttp-socks inquirer solcx
   ```
3. Configure files:
   - Add private keys to `pvkey.txt`.
   - (Optional) Add addresses to `addressFaucet.txt` or `addressERC20.txt`.
   - (Optional) Add proxies to `proxies.txt` for faucet scripts.

- **Dependencies**: Install required Python packages using:
  ```bash
  pip install -r requirements.txt

## Usage
Run the main script to access the interactive menu:
```bash
python main.py
```
The menu allows you to select tasks like:
- Faucet token $STT
- Mint $PONG, $PING, or sUSDT
- Swap $PONG -> $PING or $PING -> $PONG
- Deploy ERC20 tokens
- Send ERC20 tokens
- Mint CoNFT NFTs
- Buy/Sell meme tokens (SOMI, SMSM, SMI)

Individual scripts can be run directly, e.g.:
```bash
python scripts/mintping.py
```

## Scripts
- `main.py`: Interactive menu to run all tasks.
- `banner.py`: Displays the project banner.
- `faucetstt.py`: Claims $STT from the Somnia faucet.
- `mintping.py`: Mints $PING tokens.
- `mintpong.py`: Mints $PONG tokens.
- `mintsusdt.py`: Mints sUSDT tokens.
- `swapping.py`: Swaps $PING to $PONG.
- `swappong.py`: Swaps $PONG to $PING.
- `buymeme.py`: Buys meme tokens (SOMI, SMSM, SMI).
- `sellmeme.py`: Sells meme tokens.
- `deploytoken.py`: Deploys custom ERC20 tokens.
- `sendtoken.py`: Sends ERC20 tokens to random or file-based addresses.
- `conftnft.py`: Mints CoNFT NFTs.
- `sendtx.py`: Sends random or file-based transactions.

## Configuration
- **pvkey.txt**: Format private keys as `0x...` (one per line).
- **addressFaucet.txt**: List wallet addresses for faucet claims.
- **addressERC20.txt**: List recipient addresses for token transfers.
- **proxies.txt**: Format proxies as `socks5://user:pass@host:port` or `http://host:port`.
- **config.json**: Adjust `maxWorkers` for thread count (default: 10).

## Notes
- Ensure sufficient $STT balance in wallets for gas fees.
- Test scripts with a single wallet before running multiple wallets to avoid gas waste.
- Use proxies for faucet claims to bypass rate limits (optional).
- Check transaction status on the Somnia Testnet Explorer.
- Scripts are for educational purposes and testing on the Somnia Testnet only.

## Contributing
Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.


## Acknowledgments
Developed by Ostad kachal. For support or inquiries, visit [GitHub](https://github.com/sinak1023).

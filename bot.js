const fs = require('fs');
const { ethers } = require('ethers');

const privateKeys = fs.readFileSync('pvkey.txt', 'utf8').split('\n').filter(key => key.trim());

privateKeys.forEach(key => {
  try {
    const wallet = new ethers.Wallet(key.trim());
    console.log(wallet.address);
  } catch (error) {
    // نادیده گرفتن خطاهای کلید نامعتبر
  }
});

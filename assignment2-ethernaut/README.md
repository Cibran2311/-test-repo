# Assignment 2 — Ethernaut (real Sepolia evidence)

Network: Ethereum Sepolia (chain ID 11155111)
Player: 0xa8ECB157F6b7aE8cdcBcb62817c7Fb2d8B2a9952
Ethernaut controller: https://sepolia.etherscan.io/address/0xa3e7317E591D5A0F1c605be1b3aC4D2ae56104d6

## Completed levels

| Level | JSON difficulty | Instance | Exploit | Submit |
|---|---:|---|---|---|
| Fallout (ID 2) | 2 | https://sepolia.etherscan.io/address/0x594C5779402A7D56d189E385ED88A83718a77679 | https://sepolia.etherscan.io/tx/0xa66f9ad1ed15a0211c0134865deafbb06ae6ca771b8b4fbaef294c911069c4d2 | https://sepolia.etherscan.io/tx/0x385a48c7da7b262eaef1f6463222958644eccd61b3e204284c31ab0bcc1fbca9 |
| Token (ID 5) | 3 | https://sepolia.etherscan.io/address/0xeb1aaF96723DF79473c3a1BF1ab5CcC34631362f | https://sepolia.etherscan.io/tx/0x4edb9d54a067b8407e746ac8eef8f1668abe709df9b5e43c46e70863251f8a3f | https://sepolia.etherscan.io/tx/0x23af4a9beee4f2b3c38d0a76034271f69ff324cca3a09e2b9517aaa7dbb2bd70 |
| Force (ID 7) | 5 | https://sepolia.etherscan.io/address/0xF1eF376A8bC1895B0C98692C68362bD75a64c590 | https://sepolia.etherscan.io/tx/0x481b488888f5f103e889148a81c4810086f868df43d60a8ee32d6f5bb69e875c | https://sepolia.etherscan.io/tx/0xf25e9eaff60ee060b9ca5b0244ce018f1028326f78fd20e6a160042d8c810bb0 |

Official difficulty score: 2 + 3 + 5 = 10.

## Short write-ups

- Fallout: the misspelled constructor Fal1out() remains callable, so calling it makes the caller the owner.
- Token: the Solidity 0.6 arithmetic wraps on 20 - 21, giving the player a very large balance and satisfying the factory check.
- Force: the level has no payable entry point; a helper contract funded with 1 wei uses selfdestruct to force that wei into the instance.

This is a real Sepolia technical test from a disposable operator wallet. It is not a claim that the course's registered-wallet or group-size requirements were met. A first same-address Token transfer was not counted as completion.

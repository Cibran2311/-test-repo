"""Lab 1 / Mission 1 - Enter the Blockchain.

Sends 0.0001 ETH on Ethereum Sepolia and records every field the lab asks for.

The lab defers the recipient to the instructor; until that address is known the
transaction targets a stand-in testnet account from ~/.newuuz-labs/keys.

Run:  python send_tx.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

import eth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
AMOUNT_ETH = "0.0001"


def recipient() -> str:
    path = os.path.expanduser("~/.newuuz-labs/keys/recipients.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["recipient_main"]["address"]


def main() -> None:
    w3, acct = eth.w3_with_signer()
    to = recipient()
    value = w3.to_wei(AMOUNT_ETH, "ether")

    print(f"chain_id : {w3.eth.chain_id} (Sepolia)")
    print(f"block    : {w3.eth.block_number}")
    print(f"from     : {acct.address}")
    print(f"to       : {to}")
    print(f"value    : {AMOUNT_ETH} ETH")
    print(f"balance  : {eth.balance_eth(w3, acct.address)} ETH\n")

    nonce = w3.eth.get_transaction_count(acct.address)
    base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
    priority = w3.eth.max_priority_fee

    tx = {
        "from": acct.address,
        "to": to,
        "value": value,
        "nonce": nonce,
        "chainId": eth.CHAIN_ID,
        "gas": 21000,
        "maxFeePerGas": base_fee * 2 + priority,
        "maxPriorityFeePerGas": priority,
        "type": 2,
    }

    print("sending transaction...")
    tx_hash = w3.eth.send_transaction(tx)
    rcpt = eth.wait(w3, tx_hash, "transfer 0.0001 ETH")

    tx_data = w3.eth.get_transaction(rcpt.transactionHash)
    block = w3.eth.get_block(rcpt.blockNumber)
    fee_wei = rcpt.gasUsed * rcpt.effectiveGasPrice

    print(f"\nblock number      : {rcpt.blockNumber}")
    print(f"nonce             : {tx_data['nonce']}")
    print(f"gas limit         : {tx_data['gas']}")
    print(f"gas used          : {rcpt.gasUsed}")
    print(f"effective gas price: {w3.from_wei(rcpt.effectiveGasPrice, 'gwei')} gwei")
    print(f"transaction fee   : {w3.from_wei(fee_wei, 'ether')} ETH")
    print(f"status            : {'success' if rcpt.status == 1 else 'failed'}")

    tx_hash_hex = "0x" + rcpt.transactionHash.hex().removeprefix("0x")
    print(f"explorer          : {eth.tx_url(tx_hash_hex)}")
    eth.save_result(HERE, {
        "labs": {
            "lab1": {
                "network": "sepolia",
                "wallet": acct.address,
                "recipient": to,
                "amount_eth": AMOUNT_ETH,
                "tx_hash": tx_hash_hex,
                "explorer_url": eth.tx_url(tx_hash_hex),
                "block_number": rcpt.blockNumber,
                "status": "success" if rcpt.status == 1 else "failed",
                "recipient_note": (
                    "stand-in testnet account; replace with the instructor "
                    "address when it is published"
                ),
            }
        },
        "_lab4_source": {
            "tx_hash": tx_hash_hex,
            "nonce": tx_data["nonce"],
            "gas_limit": tx_data["gas"],
            "gas_used": rcpt.gasUsed,
            "effective_gas_price_wei": rcpt.effectiveGasPrice,
            "base_fee_per_gas_wei": block["baseFeePerGas"],
            "fee_wei": fee_wei,
            "fee_eth": str(w3.from_wei(fee_wei, "ether")),
        },
    })


if __name__ == "__main__":
    main()

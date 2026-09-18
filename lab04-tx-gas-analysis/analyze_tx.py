"""Lab 4 / Mission 4 - Read the Chain.

Re-reads the Lab 1 transaction straight from an RPC node and reconstructs every
field the lab asks about: nonce, status, gas limit, gas used and the fee.

Run:  python analyze_tx.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

import eth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LAB1_RESULT = os.path.join(HERE, "..", "lab01-wallet-first-tx", "result.json")

EXPLANATION = (
    "Gas is the unit that measures how much computation a transaction consumes. "
    "The gas limit is the ceiling the sender authorises in advance: it is the "
    "maximum amount of gas the network may charge for this transaction. Gas used "
    "is how much was actually consumed once the transaction executed. A plain ETH "
    "transfer touches no contract code, so it always consumes exactly 21000 gas, "
    "and setting a higher limit changes nothing: the unused part is not charged. "
    "The fee is gas used multiplied by the effective gas price, where under "
    "EIP-1559 that price is the block base fee plus the priority fee, capped by "
    "maxFeePerGas. If execution runs out of gas before finishing, the transaction "
    "fails, its state changes are reverted, but the gas already burned is still "
    "paid for, which is why the limit protects the sender from an unbounded charge "
    "rather than from paying at all."
)


def main() -> None:
    with open(LAB1_RESULT, encoding="utf-8") as fh:
        tx_hash = json.load(fh)["labs"]["lab1"]["tx_hash"]

    w3 = eth.connect()
    tx = w3.eth.get_transaction(tx_hash)
    rcpt = w3.eth.get_transaction_receipt(tx_hash)
    block = w3.eth.get_block(rcpt.blockNumber)

    fee_wei = rcpt.gasUsed * rcpt.effectiveGasPrice
    base_fee = block["baseFeePerGas"]
    priority_paid = rcpt.effectiveGasPrice - base_fee

    print("=== Transaction fields read from the chain ===")
    rows = [
        ("tx hash", tx_hash),
        ("block", rcpt.blockNumber),
        ("from", tx["from"]),
        ("to", tx["to"]),
        ("value", f"{w3.from_wei(tx['value'], 'ether')} ETH"),
        ("nonce", tx["nonce"]),
        ("status", "success (1)" if rcpt.status == 1 else "failed (0)"),
        ("tx type", tx["type"]),
        ("gas limit", tx["gas"]),
        ("gas used", rcpt.gasUsed),
        ("gas unused", tx["gas"] - rcpt.gasUsed),
        ("base fee", f"{w3.from_wei(base_fee, 'gwei')} gwei"),
        ("max fee", f"{w3.from_wei(tx['maxFeePerGas'], 'gwei')} gwei"),
        ("max priority fee", f"{w3.from_wei(tx['maxPriorityFeePerGas'], 'gwei')} gwei"),
        ("effective gas price", f"{w3.from_wei(rcpt.effectiveGasPrice, 'gwei')} gwei"),
        ("priority actually paid", f"{w3.from_wei(priority_paid, 'gwei')} gwei"),
        ("transaction fee", f"{w3.from_wei(fee_wei, 'ether')} ETH"),
    ]
    for k, v in rows:
        print(f"  {k:24} {v}")

    print("\n=== Fee arithmetic, verified ===")
    print(f"  gas used x effective gas price = {rcpt.gasUsed} x {rcpt.effectiveGasPrice}")
    print(f"                                 = {fee_wei} wei")
    print(f"                                 = {w3.from_wei(fee_wei, 'ether')} ETH")
    assert fee_wei == rcpt.gasUsed * rcpt.effectiveGasPrice
    assert rcpt.effectiveGasPrice == min(
        tx["maxFeePerGas"], base_fee + tx["maxPriorityFeePerGas"]
    ), "EIP-1559 pricing rule does not hold"
    print("  EIP-1559 rule holds: effective price = min(maxFee, baseFee + priorityFee)")

    print("\n=== Gas limit vs gas used ===")
    print(f"  limit authorised : {tx['gas']}")
    print(f"  actually consumed: {rcpt.gasUsed}")
    print(f"  a plain ETH transfer is fixed at 21000 gas -> "
          f"{'no headroom was needed' if tx['gas'] == rcpt.gasUsed else 'the surplus was not charged'}")

    eth.save_result(HERE, {
        "labs": {
            "lab4": {
                "tx_hash": tx_hash,
                "gas_limit": tx["gas"],
                "gas_used": rcpt.gasUsed,
                "status": "success" if rcpt.status == 1 else "failed",
                "nonce": tx["nonce"],
                "block_number": rcpt.blockNumber,
                "effective_gas_price_gwei": str(w3.from_wei(rcpt.effectiveGasPrice, "gwei")),
                "base_fee_gwei": str(w3.from_wei(base_fee, "gwei")),
                "transaction_fee_eth": str(w3.from_wei(fee_wei, "ether")),
                "explorer_url": eth.tx_url(tx_hash),
                "explanation": EXPLANATION,
            }
        }
    })


if __name__ == "__main__":
    main()

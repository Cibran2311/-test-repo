"""Lab 5 / Mission 5 - Launch Your Token.

Deploys an ERC20, reads its metadata, performs three individual transfers, then
deploys a Disperse contract and runs one batch distribution through it.

The lab points at https://disperse.app/, which is a browser interface and cannot
be driven from a script; contracts/Disperse.sol reimplements the same behaviour
(approve, then one transferFrom per recipient) so the batch transaction is real.

Run:  python run_lab5.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

from web3.logs import DISCARD  # noqa: E402

import eth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

INITIAL_SUPPLY = 1_000_000          # whole tokens, scaled by decimals in the constructor
TRANSFER_AMOUNT = 100               # STUD sent to each of the three recipients
DISPERSE_AMOUNT = 50                # STUD sent to each disperse recipient


def recipients() -> dict:
    path = os.path.expanduser("~/.newuuz-labs/keys/recipients.json")
    with open(path, encoding="utf-8") as fh:
        return {k: v["address"] for k, v in json.load(fh).items()}


def decode_transfers(w3, token, rcpt) -> list:
    """Return every ERC20 Transfer event contained in a receipt."""
    return token.events.Transfer().process_receipt(rcpt, errors=DISCARD)


def main() -> None:
    w3, acct = eth.w3_with_signer()
    rcpts = recipients()
    print(f"wallet  : {acct.address}")
    print(f"balance : {eth.balance_eth(w3, acct.address)} ETH\n")

    # ---------------------------------------------------------- Step 1: deploy
    print("=== Step 1 - deploy the ERC20 ===")
    token_addr, token, deploy_rcpt = eth.deploy(
        w3, acct, os.path.join(BUILD, "StudentToken.json"),
        INITIAL_SUPPLY, label="deploy StudentToken",
    )
    deploy_tx = "0x" + deploy_rcpt.transactionHash.hex().removeprefix("0x")

    # ------------------------------------------------------- Step 2: metadata
    print("\n=== Step 2 - token metadata read back from the chain ===")
    decimals = token.functions.decimals().call()
    total_supply = token.functions.totalSupply().call()
    meta = {
        "address": token_addr,
        "name": token.functions.name().call(),
        "symbol": token.functions.symbol().call(),
        "decimals": decimals,
        "total_supply_raw": str(total_supply),
        "total_supply": str(total_supply // 10 ** decimals),
    }
    for k, v in meta.items():
        print(f"  {k:18} {v}")
    unit = 10 ** decimals

    # ------------------------------------------------- Step 3: three transfers
    print("\n=== Step 3 - three individual transfers ===")
    transfer_txs = []
    for name in ["recipient_a", "recipient_b", "recipient_c"]:
        to = rcpts[name]
        tx_hash = token.functions.transfer(to, TRANSFER_AMOUNT * unit).transact(
            {"from": acct.address}
        )
        r = eth.wait(w3, tx_hash, f"transfer -> {name}")
        events = decode_transfers(w3, token, r)
        assert len(events) == 1, "expected exactly one Transfer event"
        ev = events[0]["args"]
        assert ev["from"] == acct.address and ev["to"] == to
        assert ev["value"] == TRANSFER_AMOUNT * unit
        transfer_txs.append("0x" + r.transactionHash.hex().removeprefix("0x"))
        print(f"       Transfer event: {ev['from'][:10]}… -> {ev['to'][:10]}… "
              f"value={ev['value'] // unit} {meta['symbol']}")

    # ------------------------------------------------- Step 4: deploy Disperse
    print("\n=== Step 4 - deploy the Disperse contract ===")
    disperse_addr, disperse, disperse_deploy = eth.deploy(
        w3, acct, os.path.join(BUILD, "Disperse.json"), label="deploy Disperse",
    )

    # ---------------------------------------------------- Step 5: approve
    print("\n=== Step 5 - approve Disperse to spend tokens ===")
    batch = ["disperse_1", "disperse_2", "disperse_3"]
    total_batch = DISPERSE_AMOUNT * unit * len(batch)
    approve_hash = token.functions.approve(disperse_addr, total_batch).transact(
        {"from": acct.address}
    )
    approve_rcpt = eth.wait(w3, approve_hash, "approve Disperse")
    allowance = token.functions.allowance(acct.address, disperse_addr).call()
    print(f"       allowance now: {allowance // unit} {meta['symbol']}")
    assert allowance == total_batch

    # ---------------------------------------------------- Step 6: batch
    print("\n=== Step 6 - one batch transaction to three recipients ===")
    addrs = [rcpts[n] for n in batch]
    values = [DISPERSE_AMOUNT * unit] * len(batch)
    batch_hash = disperse.functions.disperseTokenSimple(
        token_addr, addrs, values
    ).transact({"from": acct.address})
    batch_rcpt = eth.wait(w3, batch_hash, "disperse batch (3 recipients)")
    batch_events = decode_transfers(w3, token, batch_rcpt)
    print(f"       Transfer events in one transaction: {len(batch_events)}")
    for ev in batch_events:
        a = ev["args"]
        print(f"         {a['from'][:10]}… -> {a['to'][:10]}… "
              f"value={a['value'] // unit} {meta['symbol']}")
    assert len(batch_events) == len(batch), "expected one Transfer per recipient"

    # ---------------------------------------------------- verification
    print("\n=== Verification - balances read back from the chain ===")
    for name in ["recipient_a", "recipient_b", "recipient_c", *batch]:
        bal = token.functions.balanceOf(rcpts[name]).call()
        expected = TRANSFER_AMOUNT if name.startswith("recipient") else DISPERSE_AMOUNT
        print(f"  {name:14} {bal // unit:>5} {meta['symbol']}"
              f"  {'OK' if bal == expected * unit else 'MISMATCH'}")
        assert bal == expected * unit
    sender_left = token.functions.balanceOf(acct.address).call() // unit
    expected_left = INITIAL_SUPPLY - TRANSFER_AMOUNT * 3 - DISPERSE_AMOUNT * 3
    print(f"  {'sender':14} {sender_left:>5} {meta['symbol']}"
          f"  {'OK' if sender_left == expected_left else 'MISMATCH'}")
    assert sender_left == expected_left

    batch_tx = "0x" + batch_rcpt.transactionHash.hex().removeprefix("0x")
    eth.save_result(HERE, {
        "labs": {
            "lab5": {
                "network": "sepolia",
                "wallet": acct.address,
                "token_contract": token_addr,
                "token_name": meta["name"],
                "token_symbol": meta["symbol"],
                "token_decimals": decimals,
                "token_total_supply": meta["total_supply"],
                "deploy_tx": deploy_tx,
                "transfer_txs": transfer_txs,
                "disperse_contract": disperse_addr,
                "approval_tx": "0x" + approve_rcpt.transactionHash.hex().removeprefix("0x"),
                "disperse_tx": batch_tx,
                "disperse_recipients": addrs,
                "transfer_events_in_disperse_tx": len(batch_events),
                "explorer_token": eth.address_url(token_addr),
                "explorer_disperse_tx": eth.tx_url(batch_tx),
                "disperse_note": (
                    "disperse.app is a browser interface; contracts/Disperse.sol "
                    "reimplements the same approve + transferFrom batch pattern"
                ),
            }
        }
    })


if __name__ == "__main__":
    main()

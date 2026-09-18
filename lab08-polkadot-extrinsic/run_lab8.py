"""Lab 8 / Mission 8 - Enter Polkadot.

Submits a balance transfer extrinsic on the Westend relay chain and reads back
the resulting events.

The relay chain balance comes from the Lab 9 teleport: the faucet drips to Asset
Hub only and enforces a daily quota, so the funds were moved across with XCM
first.

The lab defers the recipient to the instructor; until that address is known the
extrinsic targets a stand-in Westend account generated alongside the others.

Run:  python run_lab8.py
"""

import json
import os
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

from substrateinterface import Keypair, KeypairType, SubstrateInterface  # noqa: E402

import keys as keystore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RELAY = "wss://westend-rpc.polkadot.io"
PLANCK = 10 ** 12
AMOUNT_WND = 1.0

RECIPIENT_FILE = os.path.expanduser("~/.newuuz-labs/keys/westend_recipient.json")


def keypair() -> Keypair:
    data = keystore.load("westend")
    return Keypair.create_from_mnemonic(
        data["mnemonic"], ss58_format=42, crypto_type=KeypairType.SR25519
    )


def recipient_address() -> str:
    """Create a stand-in recipient once, then reuse it."""
    if os.path.exists(RECIPIENT_FILE):
        with open(RECIPIENT_FILE, encoding="utf-8") as fh:
            return json.load(fh)["address"]

    mnemonic = Keypair.generate_mnemonic(words=12)
    kp = Keypair.create_from_mnemonic(mnemonic, ss58_format=42, crypto_type=KeypairType.SR25519)
    with open(RECIPIENT_FILE, "w", encoding="utf-8") as fh:
        json.dump({
            "network": "polkadot_westend",
            "role": "lab 8 stand-in recipient",
            "address": kp.ss58_address,
            "mnemonic": mnemonic,
            "warning": "TESTNET ONLY",
        }, fh, indent=2)
    os.chmod(RECIPIENT_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(f"  created a stand-in recipient, secret stored at {RECIPIENT_FILE}")
    return kp.ss58_address


def free_balance(substrate: SubstrateInterface, address: str) -> int:
    return substrate.query("System", "Account", [address]).value["data"]["free"]


def main() -> None:
    kp = keypair()
    to = recipient_address()

    substrate = SubstrateInterface(url=RELAY)
    print(f"chain     : {substrate.chain}")
    print(f"token     : {substrate.token_symbol}, {substrate.token_decimals} decimals")
    print(f"ss58 fmt  : {substrate.ss58_format}")
    print(f"signer    : {kp.ss58_address}")
    print(f"recipient : {to}")

    sender_before = free_balance(substrate, kp.ss58_address)
    recipient_before = free_balance(substrate, to)
    print(f"\n=== Balances before ===")
    print(f"  signer    : {sender_before / PLANCK:.6f} WND")
    print(f"  recipient : {recipient_before / PLANCK:.6f} WND")

    ed = substrate.get_constant("Balances", "ExistentialDeposit").value
    print(f"  existential deposit on this chain: {ed / PLANCK} WND")

    amount = int(AMOUNT_WND * PLANCK)
    print(f"\n=== Step 6 - submit the transfer extrinsic ===")
    call = substrate.compose_call(
        call_module="Balances",
        call_function="transfer_keep_alive",
        call_params={"dest": to, "value": amount},
    )
    payment = substrate.get_payment_info(call=call, keypair=kp)
    print(f"  pallet.method : Balances.transfer_keep_alive")
    print(f"  amount        : {AMOUNT_WND} WND")
    print(f"  estimated fee : {payment['partialFee'] / PLANCK:.6f} WND")

    extrinsic = substrate.create_signed_extrinsic(call=call, keypair=kp)
    print("  submitting...")
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    print(f"\n=== Step 7 - the extrinsic on chain ===")
    print(f"  extrinsic hash : {receipt.extrinsic_hash}")
    print(f"  block hash     : {receipt.block_hash}")
    block_number = receipt.block_number or substrate.get_block_number(receipt.block_hash)
    print(f"  block number   : {block_number}")
    print(f"  success        : {receipt.is_success}")
    if not receipt.is_success:
        raise RuntimeError(f"extrinsic failed: {receipt.error_message}")
    print(f"  fee paid       : {receipt.total_fee_amount / PLANCK:.6f} WND")

    print("\n  events:")
    transfer_seen = False
    events = []
    for ev in receipt.triggered_events:
        v = ev.value
        name = f"{v['module_id']}.{v['event_id']}"
        events.append(name)
        print(f"    {name}")
        if name == "Balances.Transfer":
            attrs = v["attributes"]
            print(f"      from   : {attrs['from']}")
            print(f"      to     : {attrs['to']}")
            print(f"      amount : {attrs['amount'] / PLANCK:.6f} WND")
            assert attrs["from"] == kp.ss58_address
            assert attrs["to"] == to
            assert attrs["amount"] == amount
            transfer_seen = True
    assert transfer_seen, "no Balances.Transfer event found"

    sender_after = free_balance(substrate, kp.ss58_address)
    recipient_after = free_balance(substrate, to)
    print(f"\n=== Balances after ===")
    print(f"  signer    : {sender_before / PLANCK:.6f} -> {sender_after / PLANCK:.6f} WND")
    print(f"  recipient : {recipient_before / PLANCK:.6f} -> {recipient_after / PLANCK:.6f} WND")
    assert recipient_after - recipient_before == amount
    print("  the recipient gained exactly the transferred amount  OK")
    spent = sender_before - sender_after
    print(f"  the signer spent {spent / PLANCK:.6f} WND = "
          f"{AMOUNT_WND} transferred + {(spent - amount) / PLANCK:.6f} fee")

    substrate.close()

    with open(os.path.join(HERE, "result.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "labs": {
                "lab8": {
                    "network": "westend",
                    "polkadot_wallet": kp.ss58_address,
                    "recipient": to,
                    "amount_wnd": str(AMOUNT_WND),
                    "extrinsic_hash": receipt.extrinsic_hash,
                    "block_hash": receipt.block_hash,
                    "block_number": block_number,
                    "pallet": "Balances",
                    "method": "transfer_keep_alive",
                    "fee_wnd": f"{receipt.total_fee_amount / PLANCK:.6f}",
                    "events": events,
                    "explorer_url":
                        f"https://westend.subscan.io/extrinsic/{receipt.extrinsic_hash}",
                    "recipient_note": (
                        "stand-in Westend account; replace with the instructor "
                        "address when it is published"
                    ),
                    "funding_note": (
                        "the relay balance arrived via the Lab 9 XCM teleport from "
                        "Asset Hub, because the faucet only drips to Asset Hub"
                    ),
                }
            }
        }, fh, indent=2, ensure_ascii=False)
    print(f"\nwrote {os.path.join(HERE, 'result.json')}")


if __name__ == "__main__":
    main()

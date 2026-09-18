"""Lab 9 / Mission 9 - Send a Cross-chain Message.

Performs a real XCM teleport between the Westend relay chain and Westend Asset
Hub, then reads back the resulting events on both sides.

Direction note: the lab text describes Westend -> AssetHub. The faucet drips to
Asset Hub and enforces a one-request-per-day quota, so the relay balance is
zero and the teleport runs Asset Hub -> relay instead. The XCM mechanics,
the pallet and the evidence are identical; only the source and destination are
swapped. Once the relay chain holds a balance, set DIRECTION = "relay_to_ah".

Run:  python run_lab9.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

from substrateinterface import Keypair, KeypairType, SubstrateInterface  # noqa: E402

import keys as keystore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

RELAY = "wss://westend-rpc.polkadot.io"
ASSETHUB = "wss://westend-asset-hub-rpc.polkadot.io"
ASSETHUB_PARA_ID = 1000

DIRECTION = "ah_to_relay"          # or "relay_to_ah" once the relay is funded
AMOUNT_WND = 3
PLANCK = 10 ** 12


def keypair() -> Keypair:
    data = keystore.load("westend")
    return Keypair.create_from_mnemonic(
        data["mnemonic"], ss58_format=42, crypto_type=KeypairType.SR25519
    )


def build_params(kp: Keypair, direction: str, amount: int, xcm_version: str) -> dict:
    """Build limited_teleport_assets arguments for the requested XCM version."""
    account_junction = {"AccountId32": {"network": None, "id": "0x" + kp.public_key.hex()}}

    if direction == "ah_to_relay":
        # From a parachain the relay chain is one level up: parents = 1, Here.
        dest_inner = {"parents": 1, "interior": "Here"}
    else:
        # From the relay chain a parachain is one level down: parents = 0, X1(Parachain).
        dest_inner = {"parents": 0, "interior": {"X1": {"Parachain": ASSETHUB_PARA_ID}}}

    beneficiary_inner = {"parents": 0, "interior": {"X1": account_junction}}

    # The WND being teleported is the relay chain's native asset. Seen from a
    # parachain that is one level up (parents = 1); seen from the relay chain
    # itself it is local (parents = 0).
    asset_location = {"parents": 1, "interior": "Here"} if direction == "ah_to_relay" \
        else {"parents": 0, "interior": "Here"}

    if xcm_version == "V3":
        # V3 wraps the asset id in Concrete and X1 takes a single junction.
        assets = [{"id": {"Concrete": asset_location}, "fun": {"Fungible": amount}}]
    else:
        # V4 and later drop Concrete and X1 takes a list of junctions.
        assets = [{"id": asset_location, "fun": {"Fungible": amount}}]
        beneficiary_inner = {"parents": 0, "interior": {"X1": [account_junction]}}
        if direction != "ah_to_relay":
            dest_inner = {"parents": 0, "interior": {"X1": [{"Parachain": ASSETHUB_PARA_ID}]}}

    # MultiAssets/Assets is a composite wrapping a single unnamed Vec field, and
    # scalecodec encodes that shape from a one-element tuple, not a bare list.
    assets = (assets,)

    return {
        "dest": {xcm_version: dest_inner},
        "beneficiary": {xcm_version: beneficiary_inner},
        "assets": {xcm_version: assets},
        "fee_asset_item": 0,
        "weight_limit": "Unlimited",
    }


def balances(kp: Keypair) -> dict:
    out = {}
    for label, url in [("relay", RELAY), ("assethub", ASSETHUB)]:
        s = SubstrateInterface(url=url)
        acc = s.query("System", "Account", [kp.ss58_address])
        out[label] = acc.value["data"]["free"] / PLANCK
        s.close()
    return out


def main() -> None:
    kp = keypair()
    print(f"account : {kp.ss58_address}")

    source_url = ASSETHUB if DIRECTION == "ah_to_relay" else RELAY
    src_name = "Westend Asset Hub" if DIRECTION == "ah_to_relay" else "Westend Relay"
    dst_name = "Westend Relay" if DIRECTION == "ah_to_relay" else "Westend Asset Hub"

    before = balances(kp)
    print(f"\n=== Balances before ===")
    print(f"  relay    : {before['relay']:.6f} WND")
    print(f"  assethub : {before['assethub']:.6f} WND")

    print(f"\n=== Step 1-4 - teleport {AMOUNT_WND} WND: {src_name} -> {dst_name} ===")
    substrate = SubstrateInterface(url=source_url)
    print(f"  connected to {substrate.chain}, runtime spec {substrate.runtime_version}")

    amount = AMOUNT_WND * PLANCK
    call = None
    used_version = None
    last_error = None
    for version in ["V4", "V3"]:
        try:
            params = build_params(kp, DIRECTION, amount, version)
            call = substrate.compose_call(
                call_module="PolkadotXcm",
                call_function="limited_teleport_assets",
                call_params=params,
            )
            used_version = version
            print(f"  encoded the call using XCM {version}")
            break
        except Exception as exc:  # noqa: BLE001 - try the older XCM version
            last_error = exc
            print(f"  XCM {version} encoding failed: {str(exc)[:110]}")
    if call is None:
        raise RuntimeError(f"could not encode the teleport call: {last_error}")

    payment = substrate.get_payment_info(call=call, keypair=kp)
    print(f"  estimated fee: {payment['partialFee'] / PLANCK:.6f} WND")

    extrinsic = substrate.create_signed_extrinsic(call=call, keypair=kp)
    print("  submitting...")
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

    print(f"\n=== Step 5 - the extrinsic on {src_name} ===")
    print(f"  extrinsic hash : {receipt.extrinsic_hash}")
    print(f"  block hash     : {receipt.block_hash}")
    print(f"  success        : {receipt.is_success}")
    if not receipt.is_success:
        raise RuntimeError(f"extrinsic failed: {receipt.error_message}")
    print(f"  fee paid       : {receipt.total_fee_amount / PLANCK:.6f} WND")

    print("\n  events emitted on the source chain:")
    interesting = []
    for ev in receipt.triggered_events:
        ev = ev.value
        module, event = ev["module_id"], ev["event_id"]
        if module in ("PolkadotXcm", "XcmpQueue", "ParachainSystem", "Balances", "PolkadotXcm"):
            print(f"    {module}.{event}")
            interesting.append(f"{module}.{event}")
    substrate.close()

    print("\n=== Step 5 - confirm arrival on the destination chain ===")
    import time
    for attempt in range(12):
        time.sleep(6)
        after = balances(kp)
        delivered = after["relay"] if DIRECTION == "ah_to_relay" else after["assethub"]
        baseline = before["relay"] if DIRECTION == "ah_to_relay" else before["assethub"]
        if delivered > baseline:
            print(f"  funds arrived after ~{(attempt + 1) * 6}s")
            break
        print(f"  waiting for delivery... ({(attempt + 1) * 6}s)")
    else:
        print("  WARNING: no balance change observed on the destination yet")
        after = balances(kp)

    print(f"\n=== Balances after ===")
    print(f"  relay    : {before['relay']:.6f} -> {after['relay']:.6f} WND "
          f"({after['relay'] - before['relay']:+.6f})")
    print(f"  assethub : {before['assethub']:.6f} -> {after['assethub']:.6f} WND "
          f"({after['assethub'] - before['assethub']:+.6f})")

    delivered_amount = (after["relay"] - before["relay"]) if DIRECTION == "ah_to_relay" \
        else (after["assethub"] - before["assethub"])
    print(f"\n  sent {AMOUNT_WND} WND, {delivered_amount:.6f} WND arrived; "
          f"the difference is the XCM delivery and execution fee charged on the "
          f"destination chain")

    explanation = (
        f"The action started on {src_name} and was executed on {dst_name}. The "
        f"asset moved by teleport: WND was burned on the source chain and an "
        f"equal amount minted on the destination, which is safe here because "
        f"both chains trust each other as part of one consensus system. This "
        f"differs from a normal transfer because a normal transfer changes two "
        f"balances inside a single state machine, whereas this submitted one "
        f"extrinsic on the source chain that emitted an XCM message; the "
        f"destination chain then executed that message in its own block, which "
        f"is why the funds appeared a few blocks later and why part of the "
        f"amount was consumed as execution fees on the far side. It also differs "
        f"from a bridge: no external relayer or wrapped-asset contract is "
        f"involved, the message is carried by the relay chain itself."
    )

    with open(os.path.join(HERE, "result.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "labs": {
                "lab9": {
                    "source_chain": src_name,
                    "destination_chain": dst_name,
                    "polkadot_wallet": kp.ss58_address,
                    "extrinsic_hash": receipt.extrinsic_hash,
                    "block_hash": receipt.block_hash,
                    "pallet": "PolkadotXcm",
                    "method": "limited_teleport_assets",
                    "xcm_version": used_version,
                    "amount_wnd": str(AMOUNT_WND),
                    "amount_delivered_wnd": f"{delivered_amount:.6f}",
                    "fee_wnd": f"{receipt.total_fee_amount / PLANCK:.6f}",
                    "events": interesting,
                    "explorer_url":
                        f"https://assethub-westend.subscan.io/extrinsic/{receipt.extrinsic_hash}"
                        if DIRECTION == "ah_to_relay"
                        else f"https://westend.subscan.io/extrinsic/{receipt.extrinsic_hash}",
                    "explanation": explanation,
                    "direction_note": (
                        "the lab describes Westend -> AssetHub; the faucet only "
                        "funded Asset Hub and enforces a daily quota, so the "
                        "teleport runs in the opposite direction"
                    ),
                }
            }
        }, fh, indent=2, ensure_ascii=False)
    print(f"\nwrote {os.path.join(HERE, 'result.json')}")


if __name__ == "__main__":
    main()

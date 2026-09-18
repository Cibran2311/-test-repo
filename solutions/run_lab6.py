"""Lab 6 / Mission 6 - Create and Move NFTs.

Full ERC721 flow on Sepolia:
  1. receive an NFT from the "professor" collection
  2. return it
  3. mint a personal NFT
  4. check ownerOf
  5. approve the special contract
  6. transfer the NFT into the special contract and confirm the new owner

The lab defers three addresses to the instructor (professor collection, the
special contract, and the return address). They are not published in this
repository, so contracts/ deploys stand-ins with the same interfaces. Swapping
in the real addresses means changing PROFESSOR_NFT / SPECIAL_CONTRACT below and
skipping the corresponding deploy.

Run:  python run_lab6.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

from web3.logs import DISCARD  # noqa: E402

import eth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

# Set these to the instructor's addresses once they are published; leaving them
# as None makes the script deploy its own stand-ins.
PROFESSOR_NFT = None
SPECIAL_CONTRACT = None


def recipients() -> dict:
    path = os.path.expanduser("~/.newuuz-labs/keys/recipients.json")
    with open(path, encoding="utf-8") as fh:
        return {k: v["address"] for k, v in json.load(fh).items()}


def transfer_events(nft, rcpt):
    return nft.events.Transfer().process_receipt(rcpt, errors=DISCARD)


def h(rcpt) -> str:
    return "0x" + rcpt.transactionHash.hex().removeprefix("0x")


def main() -> None:
    w3, acct = eth.w3_with_signer()
    rcpts = recipients()
    professor_address = rcpts["recipient_main"]   # stands in for the instructor
    print(f"wallet  : {acct.address}")
    print(f"balance : {eth.balance_eth(w3, acct.address)} ETH\n")

    # ------------------------------------------- Step 1: professor collection
    print("=== Step 1 - the professor collection ===")
    prof_addr, prof_nft, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "SimpleNFT.json"),
        "Professor Collection", "PROF", label="deploy professor NFT",
    )

    # ------------------------------------------- Step 2: receive the NFT
    print("\n=== Step 2 - receive the professor NFT ===")
    r = eth.wait(w3, prof_nft.functions.mint(acct.address).transact({"from": acct.address}),
                 "mint professor NFT -> wallet")
    ev = transfer_events(prof_nft, r)[0]["args"]
    prof_token_id = ev["tokenId"]
    receive_tx = h(r)
    print(f"       Transfer event: from={ev['from']} to={ev['to'][:12]}… tokenId={prof_token_id}")
    assert ev["to"] == acct.address, "the NFT must land in the student wallet"
    assert prof_nft.functions.ownerOf(prof_token_id).call() == acct.address
    print(f"       ownerOf({prof_token_id}) = student wallet  OK")

    # ------------------------------------------- Step 3: return the NFT
    print("\n=== Step 3 - return the professor NFT ===")
    r = eth.wait(
        w3,
        prof_nft.functions.transferFrom(acct.address, professor_address, prof_token_id)
        .transact({"from": acct.address}),
        "return professor NFT",
    )
    return_tx = h(r)
    ev = transfer_events(prof_nft, r)[0]["args"]
    print(f"       Transfer event: {ev['from'][:12]}… -> {ev['to'][:12]}… tokenId={ev['tokenId']}")
    owner_now = prof_nft.functions.ownerOf(prof_token_id).call()
    assert owner_now == professor_address and owner_now != acct.address
    print(f"       ownerOf({prof_token_id}) moved away from the student wallet  OK")

    # ------------------------------------------- Step 4: personal collection
    print("\n=== Step 4 - mint the personal NFT ===")
    personal_addr, personal_nft, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "SimpleNFT.json"),
        "Student Collection", "STUDNFT", label="deploy personal NFT",
    )
    r = eth.wait(w3, personal_nft.functions.mint(acct.address).transact({"from": acct.address}),
                 "mint personal NFT")
    mint_tx = h(r)
    ev = transfer_events(personal_nft, r)[0]["args"]
    personal_token_id = ev["tokenId"]
    print(f"       mint Transfer event: from={ev['from']} (zero address = mint) "
          f"tokenId={personal_token_id}")
    assert ev["from"] == "0x" + "0" * 40, "a mint must come from the zero address"

    # ------------------------------------------- Step 5: ownerOf
    print("\n=== Step 5 - check the owner ===")
    owner = personal_nft.functions.ownerOf(personal_token_id).call()
    print(f"       ownerOf({personal_token_id}) = {owner}")
    assert owner == acct.address
    print("       matches the student wallet  OK")

    # ------------------------------------------- Step 6: special contract
    print("\n=== Step 6 - deploy the special contract and approve it ===")
    special_addr, special, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "SpecialContract.json"), label="deploy SpecialContract",
    )
    r = eth.wait(
        w3,
        personal_nft.functions.approve(special_addr, personal_token_id)
        .transact({"from": acct.address}),
        "approve special contract",
    )
    approval_tx = h(r)
    approvals = personal_nft.events.Approval().process_receipt(r, errors=DISCARD)
    a = approvals[0]["args"]
    print(f"       Approval event: owner={a['owner'][:12]}… approved={a['approved'][:12]}… "
          f"tokenId={a['tokenId']}")
    assert personal_nft.functions.getApproved(personal_token_id).call() == special_addr
    print("       getApproved matches the special contract  OK")

    # ------------------------------------------- Step 7: safeTransferFrom
    print("\n=== Step 7 - move the NFT into the special contract ===")
    r = eth.wait(
        w3,
        personal_nft.functions.safeTransferFrom(
            acct.address, special_addr, personal_token_id
        ).transact({"from": acct.address}),
        "safeTransferFrom -> special",
    )
    transfer_tx = h(r)
    ev = transfer_events(personal_nft, r)[0]["args"]
    print(f"       Transfer event: {ev['from'][:12]}… -> {ev['to'][:12]}… tokenId={ev['tokenId']}")

    received = special.events.NFTReceived().process_receipt(r, errors=DISCARD)
    n = received[0]["args"]
    print(f"       NFTReceived event: collection={n['collection'][:12]}… "
          f"depositor={n['depositor'][:12]}… tokenId={n['tokenId']}")

    final_owner = personal_nft.functions.ownerOf(personal_token_id).call()
    print(f"\n       ownerOf({personal_token_id}) = {final_owner}")
    assert final_owner == special_addr, "the special contract must own the NFT now"
    print("       the special contract is now the owner  OK")

    count = special.functions.depositCount().call()
    collection, tid, depositor = special.functions.depositAt(0).call()
    print(f"       special contract records {count} deposit: "
          f"collection={collection[:12]}… tokenId={tid} depositor={depositor[:12]}…")
    assert (collection, tid, depositor) == (personal_addr, personal_token_id, acct.address)
    print("       the on-chain deposit record matches  OK")

    eth.save_result(HERE, {
        "labs": {
            "lab6": {
                "network": "sepolia",
                "wallet": acct.address,
                "professor_nft_contract": prof_addr,
                "professor_token_id": str(prof_token_id),
                "professor_nft_receive_tx": receive_tx,
                "professor_nft_return_tx": return_tx,
                "professor_return_address": professor_address,
                "personal_nft_contract": personal_addr,
                "personal_token_id": str(personal_token_id),
                "mint_tx": mint_tx,
                "special_contract": special_addr,
                "approval_tx": approval_tx,
                "transfer_to_special_contract_tx": transfer_tx,
                "final_owner": final_owner,
                "transfer_method": "safeTransferFrom",
                "explorer_personal_nft": eth.address_url(personal_addr),
                "explorer_special_contract": eth.address_url(special_addr),
                "substitution_note": (
                    "the professor collection, the return address and the special "
                    "contract are stand-ins deployed by this script; the lab text "
                    "defers those addresses to the instructor"
                ),
            }
        }
    })


if __name__ == "__main__":
    main()

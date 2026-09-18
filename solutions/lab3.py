"""Lab 3 / Mission 3 - Mine Your First Block.

Builds a Merkle tree over a list of transactions and mines a simplified block
header by searching for a nonce that satisfies a difficulty prefix.

Every step is deterministic so that a checker can recompute the Merkle root and
verify the nonce from the submitted fields alone.

Serialization rules (documented so the result is reproducible):
  leaf hash   = sha256(utf8(transaction)).hexdigest()
  inner hash  = sha256(utf8(left_hex + right_hex)).hexdigest()
  odd level   = last hash is duplicated (Bitcoin convention)
  header      = prev_hash + merkle_root + student_id + str(nonce)
  block hash  = sha256(utf8(header)).hexdigest()

Run:  python lab3.py
"""

import hashlib
import json

STUDENT_ID = "123456"          # replace with the real student ID before submitting
DIFFICULTY = "0000"            # block hash must start with this prefix
PREV_HASH = "0" * 64           # genesis block: no predecessor

TRANSACTIONS = [
    "alice->bob:10",
    "bob->carol:5",
    "carol->dave:2",
    "dave->alice:1",
    "alice->eve:7",
]


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- merkle tree
def merkle_root(transactions: list[str], verbose: bool = False) -> str:
    """Build a Merkle root; returns the single remaining hash."""
    if not transactions:
        raise ValueError("cannot build a Merkle tree over an empty list")

    level = [sha256_hex(tx) for tx in transactions]
    if verbose:
        print("Level 0 (leaf hashes):")
        for tx, h in zip(transactions, level):
            print(f"  {tx:18} -> {h}")

    depth = 0
    while len(level) > 1:
        depth += 1
        if len(level) % 2 == 1:
            level = level + [level[-1]]          # duplicate the last hash
        level = [
            sha256_hex(level[i] + level[i + 1])
            for i in range(0, len(level), 2)
        ]
        if verbose:
            print(f"Level {depth}:")
            for h in level:
                print(f"  {h}")

    return level[0]


# --------------------------------------------------------------------- mining
def build_header(prev_hash: str, root: str, student_id: str, nonce: int) -> str:
    return f"{prev_hash}{root}{student_id}{nonce}"


def mine(prev_hash: str, root: str, student_id: str, difficulty: str):
    """Increment the nonce until the block hash starts with `difficulty`."""
    nonce = 0
    while True:
        header = build_header(prev_hash, root, student_id, nonce)
        block_hash = sha256_hex(header)
        if block_hash.startswith(difficulty):
            return nonce, block_hash
        nonce += 1


def main() -> None:
    print("=== Step 1-3: Merkle tree ===")
    root = merkle_root(TRANSACTIONS, verbose=True)
    print(f"\nMerkle root: {root}\n")

    print("=== Step 4-5: mining ===")
    print(f"prev_hash  : {PREV_HASH}")
    print(f"student_id : {STUDENT_ID}")
    print(f"difficulty : {DIFFICULTY!r} (block hash must start with it)")
    nonce, block_hash = mine(PREV_HASH, root, STUDENT_ID, DIFFICULTY)
    print(f"nonce found: {nonce}")
    print(f"block hash : {block_hash}")
    print(f"attempts   : {nonce + 1}  (expected ~{16 ** len(DIFFICULTY)})\n")

    # ------------------------------------------------ independent verification
    print("=== Verification (what the checker will redo) ===")
    assert merkle_root(TRANSACTIONS) == root
    print("Merkle root recomputes from the submitted transactions  OK")
    assert sha256_hex(build_header(PREV_HASH, root, STUDENT_ID, nonce)) == block_hash
    print("nonce reproduces the submitted block hash               OK")
    assert block_hash.startswith(DIFFICULTY)
    print("block hash satisfies the difficulty                     OK")

    # ------------------------------------------- tamper test: change one tx
    print("\n=== Tamper test: change one transaction ===")
    tampered = list(TRANSACTIONS)
    tampered[1] = "bob->carol:500"
    tampered_root = merkle_root(tampered)
    print(f"original root : {root}")
    print(f"tampered root : {tampered_root}")
    tampered_hash = sha256_hex(build_header(PREV_HASH, tampered_root, STUDENT_ID, nonce))
    print(f"block hash with old nonce: {tampered_hash}")
    print(
        f"still valid? {tampered_hash.startswith(DIFFICULTY)} "
        "-> the nonce no longer works, the block must be re-mined"
    )

    fragment = {
        "labs": {
            "lab3": {
                "transactions": TRANSACTIONS,
                "merkle_root": root,
                "nonce": nonce,
                "block_hash": block_hash,
                "difficulty": DIFFICULTY,
                "prev_hash": PREV_HASH,
                "student_id": STUDENT_ID,
                "header_format": "prev_hash + merkle_root + student_id + str(nonce)",
                "hash_algorithm": "sha256",
                "script_path": "notebooks/lab3.ipynb",
            }
        }
    }
    with open("lab3_submission.json", "w", encoding="utf-8") as fh:
        json.dump(fragment, fh, indent=2, ensure_ascii=False)
    print("\nWrote lab3_submission.json")


if __name__ == "__main__":
    main()

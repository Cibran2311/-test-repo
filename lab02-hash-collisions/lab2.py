"""Lab 2 / Mission 2 - Hash Detective.

Implements a deliberately weak hash function, finds a collision by brute force,
and compares the result with SHA-256.

Run:  python lab2.py
"""

import hashlib
import itertools
import json
import string


# ---------------------------------------------------------------- weak hash
def weak_hash(data: str) -> int:
    """Sum of UTF-8 bytes modulo 256.

    Output range is only 0..255, so by the pigeonhole principle a collision
    must exist among any 257 distinct inputs.
    """
    return sum(data.encode("utf-8")) % 256


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ------------------------------------------------------------ find collision
def find_collision(alphabet: str = string.digits, max_len: int = 4):
    """Return the first pair of different inputs sharing the same weak hash."""
    seen: dict[int, str] = {}
    for length in range(1, max_len + 1):
        for tup in itertools.product(alphabet, repeat=length):
            candidate = "".join(tup)
            h = weak_hash(candidate)
            if h in seen and seen[h] != candidate:
                return seen[h], candidate, h
            seen.setdefault(h, candidate)
    raise RuntimeError("no collision found in the search space")


# ------------------------------------------------------- avalanche comparison
def avalanche_demo(a: str, b: str) -> dict:
    """Show that a 1-character change barely moves the weak hash but fully
    changes SHA-256."""
    ha, hb = sha256_hex(a), sha256_hex(b)
    differing_hex_chars = sum(1 for x, y in zip(ha, hb) if x != y)
    return {
        "input_a": a,
        "input_b": b,
        "weak_a": weak_hash(a),
        "weak_b": weak_hash(b),
        "sha256_a": ha,
        "sha256_b": hb,
        "sha256_differing_hex_chars": f"{differing_hex_chars}/64",
    }


def main() -> None:
    in1, in2, h = find_collision()

    print("=== Weak hash collision ===")
    print(f"input_1 = {in1!r}  weak_hash = {weak_hash(in1)}")
    print(f"input_2 = {in2!r}  weak_hash = {weak_hash(in2)}")
    assert in1 != in2, "inputs must differ"
    assert weak_hash(in1) == weak_hash(in2) == h, "hashes must match"
    print("collision confirmed: different inputs, identical hash\n")

    print("=== Same inputs under SHA-256 ===")
    print(f"sha256({in1!r}) = {sha256_hex(in1)}")
    print(f"sha256({in2!r}) = {sha256_hex(in2)}")
    assert sha256_hex(in1) != sha256_hex(in2)
    print("no collision: SHA-256 outputs are completely different\n")

    print("=== Avalanche effect ===")
    for k, v in avalanche_demo("blockchain", "blockchaim").items():
        print(f"{k:28} {v}")

    print(
        "\n=== Search cost ===\n"
        "weak_hash  : 256 possible outputs -> a collision appears after at most\n"
        "             257 tries (birthday bound: ~20 tries for 50% probability).\n"
        "SHA-256    : 2^256 possible outputs -> a birthday attack needs about\n"
        "             2^128 operations, which is physically infeasible."
    )

    fragment = {
        "labs": {
            "lab2": {
                "input_1": in1,
                "input_2": in2,
                "hash_1": str(weak_hash(in1)),
                "hash_2": str(weak_hash(in2)),
                "hash_function": "sum of UTF-8 bytes mod 256",
                "notebook_path": "notebooks/lab2.ipynb",
                "explanation": (
                    "The weak hash maps any input to one of only 256 values, so "
                    "collisions are guaranteed by the pigeonhole principle and "
                    "trivial to find by brute force. A hash function used in a "
                    "blockchain must be collision resistant, otherwise an attacker "
                    "could swap one transaction for another without changing the "
                    "block hash. SHA-256 has a 256-bit output and no known "
                    "practical collision attack, which is why it is used for "
                    "transaction IDs, Merkle roots and proof-of-work."
                ),
            }
        }
    }
    with open("lab2_submission.json", "w", encoding="utf-8") as fh:
        json.dump(fragment, fh, indent=2, ensure_ascii=False)
    print("\nWrote lab2_submission.json")


if __name__ == "__main__":
    main()

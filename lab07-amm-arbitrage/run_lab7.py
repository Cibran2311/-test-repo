"""Lab 7 / Mission 7 - Trade Like a DeFi Bot.

Deploys two constant-product pools with deliberately different prices, reads
their reserves, works out the profitable arbitrage direction, executes both
swaps and computes the realised profit or loss in USDC.

The lab expects instructor-provided "DEX Alpha" and "DEX Beta" addresses. They
are not published in this repository, so contracts/SimpleAMM.sol is deployed
twice with the reserve ratios from the lab's own worked example
(Alpha 1000/5000 -> 5 USDC per TEST, Beta 800/4800 -> 6 USDC per TEST).

Run:  python run_lab7.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))

from web3.logs import DISCARD  # noqa: E402

import eth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

DEC = 18
UNIT = 10 ** DEC

ALPHA_TEST, ALPHA_USDC = 1000, 5000     # price 5 USDC per TEST
BETA_TEST, BETA_USDC = 800, 4800        # price 6 USDC per TEST

TRADE_USDC = 200                        # size of the arbitrage trade


def fmt(raw: int) -> str:
    return f"{raw / UNIT:,.4f}"


def h(rcpt) -> str:
    return "0x" + rcpt.transactionHash.hex().removeprefix("0x")


def main() -> None:
    w3, acct = eth.w3_with_signer()
    print(f"wallet  : {acct.address}")
    print(f"balance : {eth.balance_eth(w3, acct.address)} ETH\n")

    # ------------------------------------------------------ deploy the tokens
    print("=== Setup - deploy TEST and USDC ===")
    test_addr, test, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "TestERC20.json"),
        "Test Token", "TEST", DEC, 1_000_000, label="deploy TEST",
    )
    usdc_addr, usdc, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "TestERC20.json"),
        "USD Coin", "USDC", DEC, 1_000_000, label="deploy USDC",
    )

    # ------------------------------------------------------- deploy the pools
    print("\n=== Setup - deploy DEX Alpha and DEX Beta ===")
    alpha_addr, alpha, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "SimpleAMM.json"), test_addr, usdc_addr,
        label="deploy DEX Alpha",
    )
    beta_addr, beta, _ = eth.deploy(
        w3, acct, os.path.join(BUILD, "SimpleAMM.json"), test_addr, usdc_addr,
        label="deploy DEX Beta",
    )

    # ------------------------------------------------------- seed liquidity
    print("\n=== Setup - seed both pools with different ratios ===")
    total_test = (ALPHA_TEST + BETA_TEST) * UNIT
    total_usdc = (ALPHA_USDC + BETA_USDC + TRADE_USDC) * UNIT
    eth.wait(w3, test.functions.approve(alpha_addr, total_test).transact({"from": acct.address}),
             "approve TEST -> Alpha")
    eth.wait(w3, usdc.functions.approve(alpha_addr, total_usdc).transact({"from": acct.address}),
             "approve USDC -> Alpha")
    eth.wait(w3, alpha.functions.addLiquidity(ALPHA_TEST * UNIT, ALPHA_USDC * UNIT)
             .transact({"from": acct.address}), "seed Alpha 1000/5000")
    eth.wait(w3, test.functions.approve(beta_addr, total_test).transact({"from": acct.address}),
             "approve TEST -> Beta")
    eth.wait(w3, usdc.functions.approve(beta_addr, total_usdc).transact({"from": acct.address}),
             "approve USDC -> Beta")
    eth.wait(w3, beta.functions.addLiquidity(BETA_TEST * UNIT, BETA_USDC * UNIT)
             .transact({"from": acct.address}), "seed Beta 800/4800")

    # ------------------------------------------------- Step 2: read reserves
    print("\n=== Step 2 - read pool reserves ===")
    a_test, a_usdc = alpha.functions.getReserves().call()
    b_test, b_usdc = beta.functions.getReserves().call()
    price_alpha = a_usdc / a_test
    price_beta = b_usdc / b_test
    print(f"  DEX Alpha  TEST={fmt(a_test):>12}  USDC={fmt(a_usdc):>12}  "
          f"price={price_alpha:.4f} USDC/TEST")
    print(f"  DEX Beta   TEST={fmt(b_test):>12}  USDC={fmt(b_usdc):>12}  "
          f"price={price_beta:.4f} USDC/TEST")

    # ------------------------------------------------- Step 3: direction
    print("\n=== Step 3 - choose the arbitrage direction ===")
    buy_on, sell_on = (alpha, beta) if price_alpha < price_beta else (beta, alpha)
    buy_name, sell_name = ("Alpha", "Beta") if price_alpha < price_beta else ("Beta", "Alpha")
    strategy = f"Buy TEST on {buy_name} (cheaper), sell TEST on {sell_name} (dearer)"
    print(f"  {strategy}")
    print(f"  spread: {abs(price_beta - price_alpha):.4f} USDC/TEST "
          f"({abs(price_beta - price_alpha) / min(price_alpha, price_beta) * 100:.2f}%)")

    # ------------------------------------------------- Step 4: quote first
    print("\n=== Step 4 - quote before trading ===")
    trade_raw = TRADE_USDC * UNIT
    quoted_test = buy_on.functions.quote(usdc_addr, trade_raw).call()
    print(f"  spending {TRADE_USDC} USDC on {buy_name} should return "
          f"{fmt(quoted_test)} TEST")
    naive = trade_raw / (price_alpha if buy_name == "Alpha" else price_beta)
    print(f"  ideal at spot price (no fee, no slippage): {fmt(int(naive))} TEST")
    print(f"  difference is the 0.3% fee plus price impact")

    usdc_before = usdc.functions.balanceOf(acct.address).call()
    test_before = test.functions.balanceOf(acct.address).call()

    # ------------------------------------------------- Step 5: first swap
    print("\n=== Step 5 - swap 1: USDC -> TEST on the cheaper pool ===")
    min_out = quoted_test * 99 // 100          # 1% slippage tolerance
    r1 = eth.wait(w3, buy_on.functions.swap(usdc_addr, trade_raw, min_out)
                  .transact({"from": acct.address}), f"swap USDC->TEST on {buy_name}")
    swap1_tx = h(r1)
    ev = buy_on.events.Swap().process_receipt(r1, errors=DISCARD)[0]["args"]
    test_received = ev["amountOut"]
    print(f"       Swap event: in={fmt(ev['amountIn'])} USDC  out={fmt(test_received)} TEST")
    print(f"       {buy_name} reserves now: TEST={fmt(ev['reserveA'])} USDC={fmt(ev['reserveB'])}")

    # ------------------------------------------------- Step 6: second swap
    print("\n=== Step 6 - swap 2: TEST -> USDC on the dearer pool ===")
    eth.wait(w3, test.functions.approve(sell_on.address, test_received)
             .transact({"from": acct.address}), f"approve TEST -> {sell_name}")
    quoted_usdc = sell_on.functions.quote(test_addr, test_received).call()
    r2 = eth.wait(w3, sell_on.functions.swap(test_addr, test_received, quoted_usdc * 99 // 100)
                  .transact({"from": acct.address}), f"swap TEST->USDC on {sell_name}")
    swap2_tx = h(r2)
    ev2 = sell_on.events.Swap().process_receipt(r2, errors=DISCARD)[0]["args"]
    usdc_received = ev2["amountOut"]
    print(f"       Swap event: in={fmt(ev2['amountIn'])} TEST  out={fmt(usdc_received)} USDC")
    print(f"       {sell_name} reserves now: TEST={fmt(ev2['reserveA'])} USDC={fmt(ev2['reserveB'])}")

    # ------------------------------------------------- Step 7: profit
    print("\n=== Step 7 - profit and loss ===")
    usdc_after = usdc.functions.balanceOf(acct.address).call()
    test_after = test.functions.balanceOf(acct.address).call()
    pnl_raw = usdc_received - trade_raw
    pnl = pnl_raw / UNIT

    print(f"  USDC spent    : {fmt(trade_raw)}")
    print(f"  USDC returned : {fmt(usdc_received)}")
    print(f"  net result    : {pnl:+.4f} USDC  ({pnl / TRADE_USDC * 100:+.2f}%)")
    print(f"  TEST position : {fmt(test_after - test_before)} (should be 0, fully round-tripped)")
    assert usdc_after - usdc_before == pnl_raw, "USDC balance change must equal the P&L"

    a_test2, a_usdc2 = alpha.functions.getReserves().call()
    b_test2, b_usdc2 = beta.functions.getReserves().call()
    print(f"\n  prices after the trade:")
    print(f"    Alpha {a_usdc2 / a_test2:.4f} USDC/TEST (was {price_alpha:.4f})")
    print(f"    Beta  {b_usdc2 / b_test2:.4f} USDC/TEST (was {price_beta:.4f})")
    print("  the spread narrowed: arbitrage is what pushes two markets back together")

    final_value = (usdc_after + int(test_after * (b_usdc2 / b_test2))) / UNIT

    eth.save_result(HERE, {
        "labs": {
            "lab7": {
                "network": "sepolia",
                "wallet": acct.address,
                "dex_alpha": alpha_addr,
                "dex_beta": beta_addr,
                "test_token": test_addr,
                "usdc_token": usdc_addr,
                "alpha_reserves": {"test": str(a_test // UNIT), "usdc": str(a_usdc // UNIT)},
                "beta_reserves": {"test": str(b_test // UNIT), "usdc": str(b_usdc // UNIT)},
                "price_alpha": f"{price_alpha:.4f}",
                "price_beta": f"{price_beta:.4f}",
                "strategy": strategy,
                "trade_size_usdc": str(TRADE_USDC),
                "swap_txs": [swap1_tx, swap2_tx],
                "test_bought": fmt(test_received),
                "usdc_returned": fmt(usdc_received),
                "profit_usdc": f"{pnl:+.4f}",
                "profit_percent": f"{pnl / TRADE_USDC * 100:+.2f}",
                "final_usdc_value": f"{final_value:.4f}",
                "alpha_reserves_after": {"test": str(a_test2 // UNIT), "usdc": str(a_usdc2 // UNIT)},
                "beta_reserves_after": {"test": str(b_test2 // UNIT), "usdc": str(b_usdc2 // UNIT)},
                "explorer_swap_1": eth.tx_url(swap1_tx),
                "explorer_swap_2": eth.tx_url(swap2_tx),
                "substitution_note": (
                    "DEX Alpha and DEX Beta are stand-in SimpleAMM deployments; the "
                    "lab defers the class DEX addresses to the instructor"
                ),
            }
        }
    })


if __name__ == "__main__":
    main()

# Lab 12 — not completed, and why

Both tracks of this lab are blocked by things outside the repository. This is a
record of what was checked, so the finding can be verified rather than taken on
trust.

## Track A — STON.fi swap

**Blocked: STON.fi has no public testnet, but the lab mandates testnet.**

The lab's Safety Notes say:

> Use testnet. Do not use real TON or real jettons.

What was checked:

| Check | Result |
|---|---|
| `https://api.ston.fi/v1/routers` | 200 — every router address is `EQ…` (mainnet form) |
| `https://testnet-api.ston.fi/v1/routers` | connection failed (`000`) — host does not resolve |
| `@ston-fi/sdk` on npm | published, `2.7.0` — the SDK exists, the testnet deployment does not |

So the swap can only be executed against mainnet routers with real TON and real
jettons, which the lab explicitly forbids. Running it anyway would cost real
money and break the lab's own safety rule, so it was not done.

## Track B — HackTON security challenge

**Blocked: challenge instances are deployed per player through TonConnect in the browser.**

What was checked:

| Check | Result |
|---|---|
| `hacktheton.com/en/level/introduction` | 200, a Next.js app shell (53 KB) |
| Contract addresses in the served HTML | none |
| Contract addresses in the JS chunks | none — the `EQ…`/`kQ…` looking strings are fragments of base64-encoded BOC data, not addresses |
| Network | the page references `testnet` and `TonConnect` |

The platform follows the Ethernaut model: connecting a wallet deploys a fresh
challenge instance for that player, and the target address only exists after
that handshake. TonConnect needs a wallet application (Tonkeeper) to approve the
session — a script-generated keypair cannot complete it.

## What would unblock this

Either of these makes the lab runnable, and neither needs much from you:

1. **For Track B** — open the level in a browser, connect Tonkeeper, let the site
   deploy your challenge instance, then send me the instance address. The exploit
   itself is contract interaction and can be scripted from there.
2. **For Track A** — an instructor decision that mainnet is acceptable, plus a
   funded mainnet wallet. Not recommended: it contradicts the lab text.

A third option is to drive the browser directly with the Chrome integration,
where you would still approve the wallet connection by hand.

## Note for the course

Lab 12 as written cannot be completed by a student who follows the safety
instructions. Track A points at a service that is mainnet-only while the lab
requires testnet. Worth either replacing STON.fi with a testnet-deployed AMM, or
marking Track B as the only viable path and stating that a Tonkeeper install is
a prerequisite.

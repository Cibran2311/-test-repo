# Assignment 3 — real Sepolia chain test

This is a real Sepolia test fixture, not LLM-generated evidence.

- Network: Ethereum Sepolia (chain ID 11155111)
- Operator: 0xa8ECB157F6b7aE8cdcBcb62817c7Fb2d8B2a9952
- Chain: ChainEntry → ChainLink-1 → ChainLink-2 → ChainLink-3 → ChainTerminal
- Start transaction: https://sepolia.etherscan.io/tx/0x839541990a31725888bb8af46437618278eb2523d09474eebef2d06b678769ab
- Verified events: ChainStarted, EntryExecuted, LinkExecuted ×3, FinalReceived, ChainCompleted

Contract addresses and all transaction hashes are recorded in the root submission.json.

This is a technical integration test with one operator wallet; it is not a claim that the course group-size requirement was met.

# README.md
# L1 Soundness Checkpoint Generator

## Overview
This repository contains a small Web3-based utility that computes a compact "soundness checkpoint" from recent L1 blocks. It is designed as a helper tool for zero-knowledge and rollup systems (for example Aztec-style rollups, Zama-based cryptographic pipelines, or any system that needs a succinct commitment to recent L1 state).

The script scans recent blocks on an EVM-compatible network, extracts key roots (stateRoot, transactionsRoot, receiptsRoot) plus block numbers, and folds them into a single rolling Keccak-256 hash. The final hex string is an L1 checkpoint that can be used as a public input for ZK circuits, batch verifiers, or off-chain monitoring jobs that track soundness of L1 ↔ L2 state.

## Files
1. app.py — main script that builds the soundness checkpoint.
2. README.md — documentation, installation, usage and notes.

## Requirements
- Python 3.10 or newer
- Network access to an Ethereum-compatible RPC endpoint
- An RPC URL (public node or your own) for mainnet, testnet, or any EVM chain

## Installation
1. Install Python 3.10+ on your system.
2. Install the Web3 dependency:
   pip install web3
3. Set an RPC endpoint via environment variable or use a direct flag:
   - Option A (recommended): set RPC_URL in your environment, for example:
     export RPC_URL="https://mainnet.infura.io/v3/your_real_key"
   - Option B: provide --rpc on the command line when running the script.

No additional dependencies are required beyond Web3.

## Usage
Basic usage (uses RPC_URL from environment if set):
   python app.py

Specify the number of recent blocks to include (default 128):
   python app.py --blocks 256

Sample every Nth block to speed up profiling (default 4):
   python app.py --blocks 512 --step 8

Override RPC URL explicitly:
   python app.py --rpc https://your-rpc-endpoint

Output JSON instead of human-readable text:
   python app.py --json

You can combine flags as needed. For example:
   python app.py --blocks 256 --step 4 --json --rpc https://your-rpc-endpoint

## What the Script Computes
For a chosen window of recent blocks it:
- Detects the current chain ID and network name (Ethereum Mainnet, Sepolia, Polygon, Optimism, Arbitrum, etc.).
- Chooses a head block (latest tip) and a starting block based on the --blocks parameter.
- Iterates backwards over the range, sampling every --step block.
- For each sampled block, reads:
  - blockNumber
  - stateRoot
  - transactionsRoot
  - receiptsRoot
- Builds a rolling Keccak-256 transcript by hashing the previous transcript value concatenated with the current block tuple.
- Returns a final Keccak-256 hex string representing the soundness checkpoint.

This checkpoint can be interpreted as a lightweight commitment to the recent L1 history and is suitable as:
- Public input for a zero-knowledge circuit (for example an Aztec-style rollup proof or soundness gadget).
- A root for an off-chain verifier that checks that some rollup or ZK system remains consistent with a specific L1 range.
- A periodic artifact for monitoring tools that track L1 integrity and soundness.

## Example Output (human-readable mode)
When run in default mode, you can expect output similar to:

- Information about the connected network (chain ID, tip block).
- Number of blocks requested, sampled blocks count, and elapsed time.
- A final line labeled:
  L1 Soundness Checkpoint (Keccak-256 hex):
  followed by a 0x-prefixed hex hash.

For example, the final section might look conceptually like:
  L1 Soundness Checkpoint (Keccak-256 hex):
     0xabcdef0123...deadbeef

This value will vary depending on the network, block range, and sampling step.

## JSON Output
When using the --json flag, the script prints a JSON document containing:
- mode: always "l1_soundness_checkpoint"
- generatedAtUtc: a UTC timestamp of when the checkpoint was created
- data: an object with fields such as:
  - chainId
  - network
  - head (tip block number)
  - start (start block number)
  - blocksRequested
  - step
  - sampledBlocks
  - elapsedSec
  - checkpointHex (the main Keccak-256 hex string)

This format is convenient for automation, CI jobs, web dashboards, and ZK proof generators that need to consume the checkpoint programmatically.

## Notes and Recommendations
- This tool does not replace a formal audited commitment scheme but provides a practical and transparent L1 soundness anchor.
- For production-grade ZK and rollup setups (Aztec, Zama-centric frameworks, custom soundness circuits), you may embed checkpointHex directly as a public input into your circuits or verification logic.
- Using a small step (for example 1 or 2) increases coverage and security at the cost of more RPC calls. A larger step trades coverage for speed.
- For high-security applications, it is recommended to:
  - Use a trusted RPC endpoint (self-hosted node or highly reliable provider).
  - Run the script from multiple independent endpoints and compare the resulting checkpointHex.
- The script is generic and works with any EVM-compatible chain as long as the Web3 RPC exposes standard block fields (stateRoot, transactionsRoot, receiptsRoot).
- Always treat this checkpoint as one piece of a broader soundness story; it is designed to integrate with ZK proofs, rollups, and soundness verifiers rather than replace them.

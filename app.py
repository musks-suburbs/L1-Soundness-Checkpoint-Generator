# app.py
import os
import sys
import time
import argparse
from typing import List, Dict, Any

from web3 import Web3

DEFAULT_RPC = os.getenv("RPC_URL", "https://mainnet.infura.io/v3/your_api_key")
DEFAULT_BLOCKS = int(os.getenv("SOUNDNESS_BLOCKS", "128"))
DEFAULT_STEP = int(os.getenv("SOUNDNESS_STEP", "4"))

NETWORKS: Dict[int, str] = {
    1: "Ethereum Mainnet",
    11155111: "Sepolia Testnet",
    10: "Optimism",
    137: "Polygon",
    42161: "Arbitrum One",
}


def network_name(cid: int) -> str:
    return NETWORKS.get(cid, f"Unknown (chain ID {cid})")


def connect(rpc: str) -> Web3:
    start = time.time()
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 25}))
    if not w3.is_connected():
        print(f"❌ Failed to connect to RPC endpoint: {rpc}", file=sys.stderr)
        sys.exit(1)
    chain_id = int(w3.eth.chain_id)
    latest = int(w3.eth.block_number)
    print(f"🌐 Connected to {network_name(chain_id)} (chainId {chain_id}), tip block = {latest}")
    print(f"⚡ RPC latency ~ {time.time() - start:.2f}s")
    return w3


def build_soundness_checkpoint(
    w3: Web3, blocks: int, step: int
) -> Dict[str, Any]:
    head = int(w3.eth.block_number)
    start = max(0, head - blocks + 1)
    numbers: List[int] = list(range(head, start - 1, -step))

    if not numbers:
        raise ValueError("No blocks selected for checkpoint (check blocks/step settings).")

    transcript = b"\x00" * 32
    sampled = 0
    t0 = time.time()

    print(f"🔍 Building L1 soundness checkpoint from {len(numbers)} sampled blocks...")
    for i, n in enumerate(numbers, 1):
        blk = w3.eth.get_block(n)
        state_root = blk.stateRoot.hex()
        receipts_root = blk.receiptsRoot.hex()
        tx_root = blk.transactionsRoot.hex()

        payload = f"{blk.number}|{state_root}|{receipts_root}|{tx_root}".encode()
        transcript = Web3.keccak(transcript + payload)
        sampled += 1

        if i % 25 == 0 or i == len(numbers):
            print(f"   ⏳ Processed {i}/{len(numbers)} blocks (current n={n})")

    elapsed = time.time() - t0
    chain_id = int(w3.eth.chain_id)

    return {
        "chainId": chain_id,
        "network": network_name(chain_id),
        "head": head,
        "start": start,
        "blocksRequested": blocks,
        "step": step,
        "sampledBlocks": sampled,
        "elapsedSec": round(elapsed, 2),
        "checkpointHex": transcript.hex(),
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Generate an L1 soundness checkpoint by hashing recent block roots "
            "for use in ZK / rollup / Aztec-style systems."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--rpc", default=DEFAULT_RPC, help="RPC URL (default from RPC_URL env)")
    ap.add_argument(
        "-b",
        "--blocks",
        type=int,
        default=DEFAULT_BLOCKS,
        help="How many recent blocks to include in the checkpoint",
    )
    ap.add_argument(
        "-s",
        "--step",
        type=int,
        default=DEFAULT_STEP,
        help="Sample every Nth block (trade-off between speed and security margin)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Print JSON only (machine-readable output)",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    print(f"📅 Run started at UTC: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")

    if args.blocks <= 0 or args.step <= 0:
        print("❌ --blocks and --step must be > 0", file=sys.stderr)
        sys.exit(1)

    if args.blocks > 200_000:
        print("⚠️  Large block window requested; this may take a long time.", file=sys.stderr)

    print(f"🔗 Using RPC endpoint: {args.rpc}")
    w3 = connect(args.rpc)

    try:
        result = build_soundness_checkpoint(w3, args.blocks, args.step)
    except Exception as e:
        print(f"❌ Failed to build checkpoint: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "mode": "l1_soundness_checkpoint",
                    "generatedAtUtc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    "data": result,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    print("")
    print(f"🌐 Network: {result['network']} (chainId {result['chainId']})")
    print(
        f"📦 Window: head={result['head']} start={result['start']} "
        f"(blocksRequested={result['blocksRequested']} step={result['step']})"
    )
    print(f"🧮 Sampled blocks: {result['sampledBlocks']}  (elapsed={result['elapsedSec']}s)")
    print("")
    print("🔐 L1 Soundness Checkpoint (Keccak-256 hex):")
    print(f"   {result['checkpointHex']}")
    print("")
    print("ℹ️  This checkpoint is a rolling commitment over (blockNumber, stateRoot, "
          "transactionsRoot, receiptsRoot) for sampled blocks.")
    print("ℹ️  It can be used as public input for ZK circuits, Aztec/Zama-style rollups, "
          "or soundness verification jobs.")
    print(f"🕒 Completed at UTC: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")


if __name__ == "__main__":
    main()

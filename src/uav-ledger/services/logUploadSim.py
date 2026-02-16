import os
import sys
import argparse
from pathlib import Path

# --- Bootstrap Django settings so we can import from storage.s3_client --- 
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # repo root (uav-ledger/)
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uavledger.settings")

import django 
django.setup()

from django.conf import settings 
from storage.s3_client import s3_client, flight_key
from typing import Optional
import hashlib
from services.uav_registry_client import (
    register_flight_on_chain,
    add_checkpoint_on_chain,
    close_flight_on_chain,
)
from services.eth_client import w3

def read_log_bytes_by_lines(path: Path):
    """
    Read the file as raw bytes and split into lines while preserving line endings.
    This ensures we do not alter the bytes that will be uploaded (important later for hashing).
    """
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)  # preserves \n / \r\n exactly as-is
    return lines

def chunk_plan(total_lines: int, chunks: int):
    """
    Returns an array of cumulative indices for each upload:
      e.g., total_lines=100, chunks=10 -> [10, 20, 30, ... , 100]
    Ensures the last chunk includes any remainder.
    """
    base = total_lines // chunks
    rem = total_lines % chunks
    out = []
    acc = 0
    for i in range(chunks):
        # Distribute the remainder into the earliest chunks
        this = base + (1 if i < rem else 0)
        acc += this
        out.append(acc)
    return out

# Hash Helpers
def rolling_seed() -> bytes:
    return b"\x00" * 32 

def rolling_update(H_prev: bytes, new_bytes: bytes) -> bytes:
    return hashlib.sha256(H_prev + new_bytes).digest()

def emit_checkpoint_to_chain(flight_id: str, seq_no: int, tip_hash_hex: str):
    """
    Ensure the flight is registered, then add a checkpoint for this upload.
    For now we just store (flightId, versionId=seq_no, hash).
    """
    if seq_no == 1:
        # First upload ⇒ register the flight
        print(f"Registering flight {flight_id} on-chain...")
        reg = register_flight_on_chain(flight_id)
        print(f"  → tx={reg['transaction_hash']} status={reg['status']}")

    print(
        f"Adding checkpoint for {flight_id} seq_no={seq_no} "
        f"hash={tip_hash_hex}"
    )
    cp = add_checkpoint_on_chain(
        flight_id=flight_id,
        version_id=seq_no,
        hash_hex=tip_hash_hex,
    )
    print(f"  → tx={cp['transaction_hash']} status={cp['status']}")


def simulate_uploads(
    source_file: Path,
    flight_id: str,
    chunks: int = 10,
    bucket: Optional[str] = None,
):
    bucket = bucket or settings.AWS_S3_BUCKET
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET is not set (check your .env and settings).")
    
    if not w3.is_connected():
        print("❌ Not connected to Ethereum node – aborting; no S3 uploads were performed.")
        return

    s3 = s3_client()
    key = flight_key(flight_id)

    lines = read_log_bytes_by_lines(source_file)
    total = len(lines)
    if total == 0:
        print("Source file appears empty—nothing to upload.")
        return

    print(f"Source: {source_file}  ({total} lines)")
    print(f"Bucket: {bucket}")
    print(f"Key:    {key}")
    print(f"Chunks: {chunks}")
    print("-" * 60)

    steps = chunk_plan(total_lines=total, chunks=chunks)

    H = rolling_seed()
    prev_upto = 0

    for seq_no, upto in enumerate(steps, start=1):
        # Rolling update w/ only new bytes since last upload
        new_segment = b"".join(lines[prev_upto:upto])  # just the delta
        H = rolling_update(H, new_segment)
        tip_hash_hex = "0x" + H.hex()

        body = b"".join(lines[:upto])
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="text/plain; charset=utf-8",
        )
        head = s3.head_object(Bucket=bucket, Key=key)
        version_id = head.get("VersionId")

        print(
            f"[{seq_no:02d}/{chunks}] lines={upto:>6}  "
            f"bytes={len(body):>8}  VersionId={version_id} tipHash={tip_hash_hex}"
        )

        prev_upto = upto

        # Send to Ethereum
        try:
            emit_checkpoint_to_chain(
                flight_id=flight_id,
                seq_no=seq_no,
                tip_hash_hex=H.hex(),  # or tip_hash_hex (with "0x")
            )
        except Exception as e:
            print(f"⚠️ Failed to emit checkpoint on-chain: {e}")

    try:
        print(f"Closing flight {flight_id} on-chain...")
        res = close_flight_on_chain(flight_id)
        print(f"  → tx={res['transaction_hash']} status={res['status']}")
    except Exception as e:
        print(f"⚠️ Failed to close flight on-chain: {e}")
    print("-" * 60)
    print("Done. You should now see multiple versions via:")
    print(f"  GET /api/storage/versions/{flight_id}")
    print("or AWS Console → S3 → your bucket → object → Versions tab.")

def main():
    parser = argparse.ArgumentParser(description="Simulate cumulative S3 uploads to create versions.")
    parser.add_argument(
        "--flight-id",
        required=True,
        help="Flight identifier (e.g., flight-001)."
    )
    parser.add_argument(
        "--source",
        default="logs/data.txt",
        help="Path to source log file."
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=10,
        help="Number of cumulative uploads (versions) to create."
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Override S3 bucket (defaults to settings.AWS_S3_BUCKET)."
    )

    args = parser.parse_args()
    source_file = Path(args.source).resolve()
    if not source_file.exists():
        print(f"Source file not found: {source_file}")
        sys.exit(1)

    simulate_uploads(
        source_file=source_file,
        flight_id=args.flight_id,
        chunks=args.chunks,
        bucket=args.bucket,
    )


if __name__ == "__main__":
    main()
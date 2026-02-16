# services/verify_flight.py

from typing import List, Dict, Any, Tuple

import hashlib
from django.conf import settings

from storage.s3_client import s3_client, flight_key
from services.uav_registry_client import (
    get_checkpoint_count_from_chain,
    get_checkpoint_from_chain,
)


def rolling_seed() -> bytes:
    return b"\x00" * 32


def rolling_update(H_prev: bytes, new_bytes: bytes) -> bytes:
    return hashlib.sha256(H_prev + new_bytes).digest()


def fetch_s3_versions_with_bodies(flight_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all S3 versions for this flight *and* download their bodies.

    Returns a list of dicts (ascending by time):
      {
        "seq_no": 1-based index in time order,
        "version_id": "...",
        "last_modified": datetime,
        "size": int,
        "body": bytes,
      }
    """
    s3 = s3_client()
    bucket = settings.AWS_S3_BUCKET
    key = flight_key(flight_id)

    resp = s3.list_object_versions(Bucket=bucket, Prefix=key)

    versions = [
        v
        for v in resp.get("Versions", [])
        if v.get("Key") == key
    ]

    # sort oldest -> newest for recomputing rolling hash
    versions.sort(key=lambda v: v["LastModified"])

    out = []
    for idx, v in enumerate(versions, start=1):
        version_id = v["VersionId"]
        obj = s3.get_object(Bucket=bucket, Key=key, VersionId=version_id)
        body = obj["Body"].read()
        out.append(
            {
                "seq_no": idx,
                "version_id": version_id,
                "last_modified": v["LastModified"],
                "size": len(body),
                "body": body,
            }
        )

    return out


def recompute_rolling_hashes(s3_versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Given S3 versions (oldest -> newest, each with 'body'), recompute the
    rolling tip hash sequence using the same scheme as logUploadSim.py.

    We assume each version is the cumulative log up to that point.
    """
    H = rolling_seed()
    prev_body = b""
    results = []

    for v in s3_versions:
        body = v["body"]

        # If body shrank, that's already suspicious; still handle gracefully
        if len(body) < len(prev_body):
            new_segment = body  # everything is "new", but we flag it below
            shrank = True
        else:
            new_segment = body[len(prev_body):]
            shrank = False

        H = rolling_update(H, new_segment)
        tip_hash_hex = "0x" + H.hex()

        results.append(
            {
                "seq_no": v["seq_no"],
                "version_id": v["version_id"],
                "size": v["size"],
                "computed_hash": tip_hash_hex,
                "shrank": shrank,
            }
        )

        prev_body = body

    return results


def fetch_onchain_checkpoints(flight_id: str) -> List[Dict[str, Any]]:
    """
    Pull all checkpoints for this flight from the registry contract.
    """
    count = get_checkpoint_count_from_chain(flight_id)
    checkpoints = []
    for i in range(count):
        cp = get_checkpoint_from_chain(flight_id, i)
        # normalize hash to lowercase 0x-prefixed string
        h = cp["hash_hex"]
        checkpoints.append(
            {
                "seq_no": i + 1,
                "hash_hex": h.lower(),
                "raw": cp,
            }
        )
    return checkpoints


def verify_flight_against_chain(
    flight_id: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Main entry point used by the Django view.

    Returns (summary, rows), where:

    summary = {
      "flight_id": ...,
      "s3_version_count": N,
      "onchain_checkpoint_count": M,
      "matched_count": K,
      "tampered": bool,
      "first_bad_seq": Optional[int],
      "error": Optional[str],
    }

    rows = [
      {
        "seq_no": 1,
        "s3_version_id": "...",
        "s3_size": 12345,
        "computed_hash": "0x...",
        "onchain_hash": "0x..." or None,
        "status": "ok" | "mismatch" | "missing_onchain" | "extra_onchain" | "shrank",
      },
      ...
    ]
    """
    summary: Dict[str, Any] = {
        "flight_id": flight_id,
        "s3_version_count": 0,
        "onchain_checkpoint_count": 0,
        "matched_count": 0,
        "tampered": False,
        "first_bad_seq": None,
        "error": None,
    }

    try:
        s3_versions = fetch_s3_versions_with_bodies(flight_id)
    except Exception as e:
        summary["error"] = f"Failed to read S3 versions: {e}"
        return summary, []

    if not s3_versions:
        summary["error"] = "No S3 versions found for this flight."
        return summary, []

    computed = recompute_rolling_hashes(s3_versions)
    try:
        checkpoints = fetch_onchain_checkpoints(flight_id)
    except Exception as e:
        summary["error"] = f"Failed to read on-chain checkpoints: {e}"
        return summary, []

    summary["s3_version_count"] = len(computed)
    summary["onchain_checkpoint_count"] = len(checkpoints)

    rows: List[Dict[str, Any]] = []
    first_bad_seq = None
    matched = 0

    max_len = max(len(computed), len(checkpoints))
    for i in range(max_len):
        comp = computed[i] if i < len(computed) else None
        cp = checkpoints[i] if i < len(checkpoints) else None

        seq_no = i + 1
        row: Dict[str, Any] = {"seq_no": seq_no}

        if comp:
            row["s3_version_id"] = comp["version_id"]
            row["s3_size"] = comp["size"]
            row["computed_hash"] = comp["computed_hash"]
        else:
            row["s3_version_id"] = None
            row["s3_size"] = None
            row["computed_hash"] = None

        row["onchain_hash"] = cp["hash_hex"] if cp else None

        # Decide status
        if comp and comp["shrank"]:
            status = "shrank"
        elif comp and cp:
            # normalize hashes
            ch = comp["computed_hash"].lower()
            oh = cp["hash_hex"].lower()
            if ch == oh:
                status = "ok"
                matched += 1
            else:
                status = "mismatch"
        elif comp and not cp:
            status = "missing_onchain"
        elif cp and not comp:
            status = "extra_onchain"
        else:
            status = "unknown"

        row["status"] = status

        if status not in ("ok",) and first_bad_seq is None:
            first_bad_seq = seq_no

        rows.append(row)

    summary["matched_count"] = matched
    summary["tampered"] = first_bad_seq is not None
    summary["first_bad_seq"] = first_bad_seq

    return summary, rows

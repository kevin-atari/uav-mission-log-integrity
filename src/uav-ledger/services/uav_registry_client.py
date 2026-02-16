# services/uav_registry_client.py

from typing import Dict, Any

from web3 import Web3

from .eth_client import (
    w3,
    ACCOUNT_ADDRESS,
    ETH_PRIVATE_KEY,
    CHAIN_ID,
    CONTRACT_ADDRESS,
    mission_id_to_bytes32,  # reuse the same keccak helper for IDs
)

# =========================
#  UavFlightRegistry ABI
# =========================

UAV_FLIGHT_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"}
        ],
        "name": "registerFlight",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"},
            {"internalType": "uint256", "name": "versionId", "type": "uint256"},
            {"internalType": "bytes32", "name": "hash", "type": "bytes32"},
        ],
        "name": "addCheckpoint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"}
        ],
        "name": "closeFlight",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"}
        ],
        "name": "flightExists",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"}
        ],
        "name": "isFlightClosed",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"}
        ],
        "name": "getCheckpointCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "flightId", "type": "bytes32"},
            {"internalType": "uint256", "name": "index", "type": "uint256"},
        ],
        "name": "getCheckpoint",
        "outputs": [
            {"internalType": "uint256", "name": "versionId", "type": "uint256"},
            {"internalType": "bytes32", "name": "hash", "type": "bytes32"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def get_uav_contract():
    """
    Build a Web3 contract object for UavFlightRegistry using the
    same CONTRACT_ADDRESS and RPC connection from eth_client.py.
    """
    return w3.eth.contract(address=CONTRACT_ADDRESS, abi=UAV_FLIGHT_REGISTRY_ABI)


# =========================
#  Helper functions
# =========================

def flight_id_to_bytes32(flight_id: str) -> bytes:
    """
    Convert a human-readable flight_id string into bytes32.

    We reuse keccak hash so:
      - input: "flight-2025-11-29-uav01"
      - result: 32-byte hash used as key in the contract.
    """
    return mission_id_to_bytes32(flight_id)


def normalize_hash(hash_hex: str) -> bytes:
    """
    Normalize a hex string into a bytes32 value.
    Accepts forms like:
      - "0xabc123..."
      - "abc123..."
    """
    h = hash_hex.strip().lower()
    if h.startswith("0x"):
        h = h[2:]
    if len(h) != 64:
        raise ValueError("Hash must be 32 bytes (64 hex chars)")
    return bytes.fromhex(h)


# =========================
#  Write operations
# =========================

def register_flight_on_chain(flight_id: str) -> Dict[str, Any]:
    """
    Calls registerFlight(flightId) on UavFlightRegistry.

    Off-chain flight_id (string) -> bytes32 key via keccak.
    """
    if not w3.is_connected():
        raise RuntimeError("Not connected to Ethereum node")

    contract = get_uav_contract()
    flight_key = flight_id_to_bytes32(flight_id)

    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    tx = contract.functions.registerFlight(flight_key).build_transaction(
        {
            "from": ACCOUNT_ADDRESS,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ETH_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {
        "flight_id": flight_id,
        "flight_key": flight_key.hex(),
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt["blockNumber"],
        "status": receipt["status"],
    }


def add_checkpoint_on_chain(
    flight_id: str, version_id: int, hash_hex: str
) -> Dict[str, Any]:
    """
    Calls addCheckpoint(flightId, versionId, hash) on UavFlightRegistry.

    - flight_id: human-readable ID (we hash to bytes32)
    - version_id: 1, 2, 3, ... (for each checkpoint)
    - hash_hex: SHA-256 hash of the log version as hex string
    """
    if not w3.is_connected():
        raise RuntimeError("Not connected to Ethereum node")

    if version_id <= 0:
        raise ValueError("version_id must be > 0")

    contract = get_uav_contract()
    flight_key = flight_id_to_bytes32(flight_id)
    hash_bytes32 = normalize_hash(hash_hex)  # already 32-byte value

    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    tx = contract.functions.addCheckpoint(
        flight_key, version_id, hash_bytes32
    ).build_transaction(
        {
            "from": ACCOUNT_ADDRESS,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ETH_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {
        "flight_id": flight_id,
        "flight_key": flight_key.hex(),
        "version_id": version_id,
        "hash_hex": hash_hex,
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt["blockNumber"],
        "status": receipt["status"],
    }


def close_flight_on_chain(flight_id: str) -> Dict[str, Any]:
    """
    Calls closeFlight(flightId) to finalize a flight.
    """
    if not w3.is_connected():
        raise RuntimeError("Not connected to Ethereum node")

    contract = get_uav_contract()
    flight_key = flight_id_to_bytes32(flight_id)

    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    tx = contract.functions.closeFlight(flight_key).build_transaction(
        {
            "from": ACCOUNT_ADDRESS,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ETH_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {
        "flight_id": flight_id,
        "flight_key": flight_key.hex(),
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt["blockNumber"],
        "status": receipt["status"],
    }


# =========================
#  Read operations
# =========================

def get_checkpoint_count_from_chain(flight_id: str) -> int:
    """
    Calls getCheckpointCount(flightId) and returns how many checkpoints exist.
    """
    if not w3.is_connected():
        raise RuntimeError("Not connected to Ethereum node")

    contract = get_uav_contract()
    flight_key = flight_id_to_bytes32(flight_id)

    return contract.functions.getCheckpointCount(flight_key).call()


def get_checkpoint_from_chain(flight_id: str, index: int) -> Dict[str, Any]:
    """
    Calls getCheckpoint(flightId, index) and returns structured data.
    """
    if not w3.is_connected():
        raise RuntimeError("Not connected to Ethereum node")

    contract = get_uav_contract()
    flight_key = flight_id_to_bytes32(flight_id)

    version_id, hash_bytes32, timestamp = contract.functions.getCheckpoint(
        flight_key, index
    ).call()

    return {
        "flight_id": flight_id,
        "flight_key": flight_key.hex(),
        "index": index,
        "version_id": int(version_id),
        "hash_hex": Web3.to_hex(hash_bytes32),
        "timestamp": int(timestamp),
    }


# =========================
#  Simple smoke test
# =========================

if __name__ == "__main__":
    # Quick end-to-end test:
    # 1) register a flight
    # 2) add a fake checkpoint
    # 3) read it back
    test_flight_id = "demo-flight-002"
    print(f"Using flight_id = {test_flight_id!r}")
    print("Account:", ACCOUNT_ADDRESS)
    print("Contract:", CONTRACT_ADDRESS)

    if not w3.is_connected():
        print("❌ Not connected to Ethereum node")
    else:
        print("✅ Connected to Ethereum node")

    # 1) Register flight
    print("\n=== Register flight ===")
    reg = register_flight_on_chain(test_flight_id)
    print(reg)

    # 2) Add checkpoint with a dummy SHA-256 hash
    # (64 hex chars = 32 bytes)
    print("\n=== Add checkpoint ===")
    fake_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    cp = add_checkpoint_on_chain(test_flight_id, version_id=1, hash_hex=fake_hash)
    print(cp)

    # 3) Read back
    print("\n=== Checkpoint count ===")
    count = get_checkpoint_count_from_chain(test_flight_id)
    print("Checkpoint count:", count)

    print("\n=== First checkpoint ===")
    cp0 = get_checkpoint_from_chain(test_flight_id, 0)
    print(cp0)

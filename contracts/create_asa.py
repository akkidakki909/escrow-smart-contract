"""
CampusToken (ASA) Creation Script
Creates the CampusToken ASA on Algorand Testnet.
"""

from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
import json
import os

# ---------- Configuration ----------
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")  # algonode.cloud needs no token

# Admin account — the deployer. Set via env or generate fresh.
ADMIN_MNEMONIC = os.getenv("ADMIN_MNEMONIC", "")


def get_algod_client():
    """Return an algod client connected to Algorand Testnet."""
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def create_campus_token(client, admin_sk, admin_addr):
    """
    Create the CampusToken ASA.

    Returns:
        int: The ASA ID of the newly created CampusToken.
    """
    params = client.suggested_params()

    txn = transaction.AssetConfigTxn(
        sender=admin_addr,
        sp=params,
        total=1_000_000_000,          # 1 billion tokens
        default_frozen=False,
        unit_name="CAMPUS",
        asset_name="CampusToken",
        decimals=0,                    # 1 token = ₹1
        manager=admin_addr,
        reserve=admin_addr,
        freeze=admin_addr,
        clawback=admin_addr,
        url="https://campuschain.dev",
        note=b"CampusChain MVP Token",
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    print(f"ASA creation txn sent: {tx_id}")

    # Wait for confirmation
    result = transaction.wait_for_confirmation(client, tx_id, 4)
    asa_id = result["asset-index"]
    print(f"CampusToken created! ASA ID: {asa_id}")
    return asa_id


def main():
    if not ADMIN_MNEMONIC:
        # Generate a new account for demo purposes
        sk, addr = account.generate_account()
        mn = mnemonic.from_private_key(sk)
        print("=" * 60)
        print("No ADMIN_MNEMONIC set. Generated a new account:")
        print(f"  Address:  {addr}")
        print(f"  Mnemonic: {mn}")
        print()
        print("Fund this account on Algorand Testnet Faucet:")
        print("  https://bank.testnet.algorand.network/")
        print()
        print("Then set ADMIN_MNEMONIC env var and re-run.")
        print("=" * 60)
        return

    admin_sk = mnemonic.to_private_key(ADMIN_MNEMONIC)
    admin_addr = account.address_from_private_key(admin_sk)
    print(f"Admin address: {admin_addr}")

    client = get_algod_client()
    asa_id = create_campus_token(client, admin_sk, admin_addr)

    # Save config for other scripts
    config = {
        "admin_address": admin_addr,
        "asa_id": asa_id,
        "network": "testnet",
    }
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config saved to {config_path}")


if __name__ == "__main__":
    main()

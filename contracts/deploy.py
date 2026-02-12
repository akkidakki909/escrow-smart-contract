"""
Deploy & Bootstrap Script for CampusVault

Steps:
  1. Compile the PyTeal contract to TEAL
  2. Deploy the application to Algorand Testnet
  3. Fund the application account with ALGO (for inner txn fees)
  4. Bootstrap the application with the ASA ID
  5. Transfer CampusTokens to the application address
"""

from algosdk import account, mnemonic, transaction, logic
from algosdk.v2client import algod
import base64
import json
import os

# ---------- Configuration ----------
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")
ADMIN_MNEMONIC = os.getenv("ADMIN_MNEMONIC", "")

BUILD_DIR = os.path.join(os.path.dirname(__file__), "build")


def get_algod_client():
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def compile_program(client, source_code):
    """Compile TEAL source to bytes."""
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response["result"])


def deploy_vault(client, admin_sk, admin_addr):
    """Deploy the CampusVault application."""

    # Read compiled TEAL
    with open(os.path.join(BUILD_DIR, "campus_vault_approval.teal")) as f:
        approval_src = f.read()
    with open(os.path.join(BUILD_DIR, "campus_vault_clear.teal")) as f:
        clear_src = f.read()

    approval_prog = compile_program(client, approval_src)
    clear_prog = compile_program(client, clear_src)

    # Global: 2 keys (admin, asa_id) — both uint/bytes
    global_schema = transaction.StateSchema(num_uints=1, num_byte_slices=1)
    local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    params = client.suggested_params()

    txn = transaction.ApplicationCreateTxn(
        sender=admin_addr,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_prog,
        clear_program=clear_prog,
        global_schema=global_schema,
        local_schema=local_schema,
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    print(f"Deploy txn sent: {tx_id}")

    result = transaction.wait_for_confirmation(client, tx_id, 4)
    app_id = result["application-index"]
    app_addr = logic.get_application_address(app_id)
    print(f"CampusVault deployed! App ID: {app_id}")
    print(f"Application address: {app_addr}")

    return app_id, app_addr


def fund_app_account(client, admin_sk, admin_addr, app_addr, amount=1_000_000):
    """Send ALGO to the application account for inner txn fees."""
    params = client.suggested_params()
    txn = transaction.PaymentTxn(
        sender=admin_addr,
        sp=params,
        receiver=app_addr,
        amt=amount,  # 1 ALGO in microAlgos
    )
    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    print(f"Funded app account with {amount} microAlgos")


def bootstrap_vault(client, admin_sk, admin_addr, app_id, asa_id):
    """Call bootstrap method to store ASA ID and opt contract into ASA."""
    params = client.suggested_params()

    txn = transaction.ApplicationCallTxn(
        sender=admin_addr,
        sp=params,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=["bootstrap", asa_id],
        foreign_assets=[asa_id],
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    print(f"Vault bootstrapped with ASA ID: {asa_id}")


def seed_vault_with_tokens(client, admin_sk, admin_addr, app_addr, asa_id, amount):
    """Transfer CampusTokens from admin to the vault application address."""
    params = client.suggested_params()

    txn = transaction.AssetTransferTxn(
        sender=admin_addr,
        sp=params,
        receiver=app_addr,
        amt=amount,
        index=asa_id,
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    print(f"Transferred {amount} CampusTokens to vault")


def main():
    if not ADMIN_MNEMONIC:
        print("Error: set ADMIN_MNEMONIC env var first.")
        print("Run create_asa.py first if you haven't yet.")
        return

    # Load ASA config
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        print("Error: config.json not found. Run create_asa.py first.")
        return

    with open(config_path) as f:
        config = json.load(f)

    asa_id = config["asa_id"]
    admin_sk = mnemonic.to_private_key(ADMIN_MNEMONIC)
    admin_addr = account.address_from_private_key(admin_sk)
    client = get_algod_client()

    # Step 1: Compile PyTeal (run campus_vault.py first)
    if not os.path.exists(os.path.join(BUILD_DIR, "campus_vault_approval.teal")):
        print("TEAL files not found. Compiling PyTeal...")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'campus_vault.py')}")

    # Step 2: Deploy
    app_id, app_addr = deploy_vault(client, admin_sk, admin_addr)

    # Step 3: Fund app account
    fund_app_account(client, admin_sk, admin_addr, app_addr)

    # Step 4: Bootstrap
    bootstrap_vault(client, admin_sk, admin_addr, app_id, asa_id)

    # Step 5: Seed vault with tokens
    seed_vault_with_tokens(client, admin_sk, admin_addr, app_addr, asa_id, 100_000_000)

    # Save full config
    config["app_id"] = app_id
    config["app_address"] = app_addr
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config updated: {config_path}")
    print("Deployment complete!")


if __name__ == "__main__":
    main()

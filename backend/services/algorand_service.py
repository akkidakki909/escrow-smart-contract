"""
CampusChain Backend — Algorand Service (Custodial)

CUSTODIAL MODEL: All transactions are signed by the backend using
mnemonics stored in the database. No user ever touches a wallet.

Functions:
  - create_wallet()         → generate new Algorand account
  - get_token_balance()     → query ASA balance
  - opt_in_asa()            → opt an account into CampusToken
  - fund_student()          → admin → student ASA transfer
  - transfer_student_to_vendor() → student → vendor ASA transfer (backend-signed)
"""

from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
import json

from config import ALGOD_ADDRESS, ALGOD_TOKEN, ADMIN_MNEMONIC, ASA_ID


def get_algod_client():
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def get_admin_keys():
    """Return (private_key, address) for the admin account."""
    sk = mnemonic.to_private_key(ADMIN_MNEMONIC)
    addr = account.address_from_private_key(sk)
    return sk, addr


def create_wallet():
    """
    Generate a new Algorand account for custodial use.
    Returns (address, mnemonic_phrase).
    """
    sk, addr = account.generate_account()
    mn = mnemonic.from_private_key(sk)
    return addr, mn


def get_token_balance(address):
    """Get the CampusToken balance for an address."""
    try:
        client = get_algod_client()
        account_info = client.account_info(address)
        for asset in account_info.get("assets", []):
            if asset["asset-id"] == ASA_ID:
                return asset["amount"]
    except Exception:
        pass
    return 0


def opt_in_asa(user_mnemonic):
    """
    Opt an account into CampusToken ASA.
    Backend signs using the stored mnemonic — user doesn't need to do anything.
    """
    client = get_algod_client()
    sk = mnemonic.to_private_key(user_mnemonic)
    addr = account.address_from_private_key(sk)
    params = client.suggested_params()

    txn = transaction.AssetTransferTxn(
        sender=addr,
        sp=params,
        receiver=addr,
        amt=0,
        index=ASA_ID,
    )

    signed_txn = txn.sign(sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id


def fund_student(student_addr, amount):
    """
    Transfer CampusTokens from admin reserve → student wallet.
    Called when a parent "funds" the student via simulated UPI.
    Backend signs with admin key — parent never touches crypto.
    """
    client = get_algod_client()
    admin_sk, admin_addr = get_admin_keys()
    params = client.suggested_params()

    txn = transaction.AssetTransferTxn(
        sender=admin_addr,
        sp=params,
        receiver=student_addr,
        amt=amount,
        index=ASA_ID,
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id


def transfer_student_to_vendor(student_mnemonic, vendor_addr, amount, category):
    """
    Transfer CampusTokens from student → vendor.
    Backend signs using the student's custodial mnemonic.
    Attaches category in the note field for on-chain traceability.
    """
    client = get_algod_client()
    sk = mnemonic.to_private_key(student_mnemonic)
    student_addr = account.address_from_private_key(sk)
    params = client.suggested_params()

    note = json.dumps({"cat": category}).encode()

    txn = transaction.AssetTransferTxn(
        sender=student_addr,
        sp=params,
        receiver=vendor_addr,
        amt=amount,
        index=ASA_ID,
        note=note,
    )

    signed_txn = txn.sign(sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id


def fund_account_with_algo(target_addr, microalgos=500_000):
    """
    Send ALGO from admin to target account (for minimum balance / txn fees).
    Each account needs ~0.2 ALGO to exist + hold an ASA.
    """
    client = get_algod_client()
    admin_sk, admin_addr = get_admin_keys()
    params = client.suggested_params()

    txn = transaction.PaymentTxn(
        sender=admin_addr,
        sp=params,
        receiver=target_addr,
        amt=microalgos,
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id

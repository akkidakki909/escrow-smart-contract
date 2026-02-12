"""
CampusChain Backend — Algorand Service

Wraps py-algorand-sdk for:
  - ASA opt-in
  - Token transfers (admin → student)
  - Student → Vendor payments
  - Balance queries
"""

from algosdk import account, mnemonic, transaction, logic
from algosdk.v2client import algod
import json
import os

from config import ALGOD_ADDRESS, ALGOD_TOKEN, ADMIN_MNEMONIC, ASA_ID, APP_ID


def get_algod_client():
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def get_admin_keys():
    """Return (private_key, address) for the admin account."""
    sk = mnemonic.to_private_key(ADMIN_MNEMONIC)
    addr = account.address_from_private_key(sk)
    return sk, addr


def get_token_balance(address):
    """Get the CampusToken balance for an address."""
    client = get_algod_client()
    account_info = client.account_info(address)
    for asset in account_info.get("assets", []):
        if asset["asset-id"] == ASA_ID:
            return asset["amount"]
    return 0


def opt_in_asa(user_sk, user_addr):
    """Opt a user into the CampusToken ASA."""
    client = get_algod_client()
    params = client.suggested_params()

    txn = transaction.AssetTransferTxn(
        sender=user_addr,
        sp=params,
        receiver=user_addr,
        amt=0,
        index=ASA_ID,
    )

    signed_txn = txn.sign(user_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id


def fund_student_via_vault(student_addr, amount):
    """
    Fund a student by calling CampusVault.fund_student().
    Transfers CampusTokens from the vault to the student.
    """
    client = get_algod_client()
    admin_sk, admin_addr = get_admin_keys()
    params = client.suggested_params()

    txn = transaction.ApplicationCallTxn(
        sender=admin_addr,
        sp=params,
        index=APP_ID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=["fund_student", bytes.fromhex(student_addr) if len(student_addr) == 64 else
                  transaction.encoding.decode_address(student_addr), amount],
        foreign_assets=[ASA_ID],
        accounts=[student_addr],
    )

    signed_txn = txn.sign(admin_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id


def fund_student_direct(student_addr, amount):
    """
    Simpler alternative: direct ASA transfer from admin → student.
    Use this if the smart contract isn't deployed yet (MVP fallback).
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


def pay_vendor(student_sk, student_addr, vendor_addr, amount, category):
    """
    Student pays a vendor — plain ASA transfer with category note.
    """
    client = get_algod_client()
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

    signed_txn = txn.sign(student_sk)
    tx_id = client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(client, tx_id, 4)
    return tx_id

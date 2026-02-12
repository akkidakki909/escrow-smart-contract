"""
CampusVault — PyTeal Smart Contract

A stateful Algorand application that acts as the central treasury
for the CampusChain system. It holds CampusTokens and disburses
them to student wallets when the backend admin triggers a funding
operation.

Methods:
  - bootstrap(asa_id):       Store ASA ID, opt contract into the ASA
  - fund_student(addr, amt): Transfer tokens from vault → student
"""

from pyteal import *


def approval_program():
    """CampusVault approval program."""

    # ---------- Global state keys ----------
    admin_key = Bytes("admin")
    asa_id_key = Bytes("asa_id")

    # ---------- Scratch vars ----------
    i = ScratchVar(TealType.uint64)

    # ---------- Handlers ----------

    # --- On creation: store the creator as admin ---
    on_create = Seq(
        App.globalPut(admin_key, Txn.sender()),
        App.globalPut(asa_id_key, Int(0)),
        Approve(),
    )

    # --- Bootstrap: store ASA ID and opt the contract into the ASA ---
    asa_id_arg = Btoi(Txn.application_args[1])

    on_bootstrap = Seq(
        # Only admin can bootstrap
        Assert(Txn.sender() == App.globalGet(admin_key)),
        # Store ASA ID
        App.globalPut(asa_id_key, asa_id_arg),
        # Opt-in to the ASA via inner transaction
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: asa_id_arg,
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0),  # 0-amount = opt-in
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )

    # --- Fund Student: transfer tokens from vault to student ---
    student_addr_arg = Txn.application_args[1]
    amount_arg = Btoi(Txn.application_args[2])

    on_fund_student = Seq(
        # Only admin can fund
        Assert(Txn.sender() == App.globalGet(admin_key)),
        # Amount must be > 0
        Assert(amount_arg > Int(0)),
        # Transfer ASA tokens via inner transaction
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: App.globalGet(asa_id_key),
            TxnField.asset_receiver: student_addr_arg,
            TxnField.asset_amount: amount_arg,
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )

    # ---------- Router ----------
    method = Txn.application_args[0]

    on_call = Cond(
        [method == Bytes("bootstrap"), on_bootstrap],
        [method == Bytes("fund_student"), on_fund_student],
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        [Txn.on_completion() == OnComplete.DeleteApplication,
         Return(Txn.sender() == App.globalGet(admin_key))],
        [Txn.on_completion() == OnComplete.UpdateApplication,
         Return(Txn.sender() == App.globalGet(admin_key))],
    )

    return program


def clear_state_program():
    """Always approve clear state."""
    return Approve()


if __name__ == "__main__":
    # Compile and write TEAL files
    import os

    output_dir = os.path.join(os.path.dirname(__file__), "build")
    os.makedirs(output_dir, exist_ok=True)

    approval_teal = compileTeal(
        approval_program(), mode=Mode.Application, version=8
    )
    clear_teal = compileTeal(
        clear_state_program(), mode=Mode.Application, version=8
    )

    approval_path = os.path.join(output_dir, "campus_vault_approval.teal")
    clear_path = os.path.join(output_dir, "campus_vault_clear.teal")

    with open(approval_path, "w") as f:
        f.write(approval_teal)
    print(f"Approval program written to {approval_path}")

    with open(clear_path, "w") as f:
        f.write(clear_teal)
    print(f"Clear program written to {clear_path}")

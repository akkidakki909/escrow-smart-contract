# CampusChain — Architecture & Design Document

> **Programmable Campus Wallet System on Algorand Testnet**
> Hackathon MVP | February 2026

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Student Wallet   │  │ Parent Dashboard  │  │  Vendor Terminal  │  │
│  │  - Balance view   │  │ - Aggregated view │  │  - Accept payment │  │
│  │  - Scan/Pay QR    │  │ - Fund wallet     │  │  - Category tag   │  │
│  │  - Opt-in ASA     │  │ - NO raw txns     │  │  - QR generation  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
└───────────┼──────────────────────┼──────────────────────┼───────────┘
            │         REST API     │                      │
            ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND API (Flask/Python)                       │
│                                                                     │
│  ┌────────────┐ ┌────────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ Auth       │ │ Fund Service   │ │ Spend Indexer│ │ Aggregation│ │
│  │ (JWT)      │ │ (Sim. UPI →    │ │ (Poll Algo   │ │ API        │ │
│  │            │ │  Mint tokens)  │ │  Indexer for  │ │ (Category  │ │
│  │            │ │                │ │  student txns)│ │  summaries)│ │
│  └────────────┘ └───────┬────────┘ └──────┬───────┘ └────────────┘ │
│                         │                 │                         │
│                    ┌────┴─────────────────┴────┐                   │
│                    │   SQLite / PostgreSQL DB   │                   │
│                    │  - users, wallets          │                   │
│                    │  - category_spending (agg) │                   │
│                    │  - vendor_registry         │                   │
│                    └───────────────────────────-┘                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  Algorand SDK (py-algorand-sdk)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  ALGORAND TESTNET (Smart Contract Layer)             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  CampusToken (ASA ID: created at deploy)                    │   │
│  │  - 1 token = ₹1 (0 decimals)                               │   │
│  │  - Manager/Reserve/Freeze/Clawback = Admin account          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  CampusVault (Application / Smart Contract - PyTeal)        │   │
│  │  - Global: admin_address, asa_id                            │   │
│  │  - Methods:                                                 │   │
│  │      fund_student(student_addr, amount)  → inner ASA txn    │   │
│  │  - Only callable by admin                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  On-Chain Spending:                                          │   │
│  │  Student → Vendor = plain ASA transfer                       │   │
│  │  Note field: {"cat":"food"} | {"cat":"events"} | etc.        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Token Design — CampusToken (CAMPUS)

| Property       | Value                                                  |
|----------------|--------------------------------------------------------|
| **Type**       | Algorand Standard Asset (ASA)                          |
| **Unit Name**  | `CAMPUS`                                               |
| **Asset Name** | `CampusToken`                                          |
| **Decimals**   | `0` (1 token = ₹1, integer precision)                  |
| **Total Supply** | `1,000,000,000` (1 billion — admin-minted on demand) |
| **Manager**    | Admin/Backend wallet                                   |
| **Reserve**    | CampusVault application address                        |
| **Freeze**     | Admin wallet (disabled in normal flow)                 |
| **Clawback**   | Admin wallet (emergency refunds only)                  |

### Token Lifecycle

```
Admin creates ASA (one-time)
     │
     ▼
Parent funds student (₹500)
     │
     ▼
Backend mints/transfers 500 CAMPUS tokens
from Admin Reserve → Student Wallet
     │
     ▼
Student pays vendor (50 CAMPUS)
Student Wallet → Vendor Wallet (ASA Transfer + note)
     │
     ▼
Vendor redeems tokens for fiat (out of scope for MVP)
```

---

## 3. Smart Contract Logic (PyTeal)

### 3.1 ASA Creation Script

**File:** `contracts/create_asa.py`

Creates the CampusToken ASA on Algorand Testnet. The admin account is the
creator and holds all management roles. The total supply sits in the admin
account's reserve until distributed.

### 3.2 CampusVault Smart Contract

**File:** `contracts/campus_vault.py`

A stateful application written in PyTeal that acts as the central treasury.

**Global State:**
- `admin` — address of the backend admin wallet
- `asa_id` — the ASA ID of CampusToken

**Methods:**

| Method | Args | Logic |
|--------|------|-------|
| `bootstrap` | `asa_id` | Store ASA ID, opt the contract into the ASA |
| `fund_student` | `student_addr`, `amount` | Verify caller is admin, execute inner ASA transfer from contract → student |

**Security:**
- Only the admin address can call `fund_student`
- Amount must be > 0
- Student must have opted into the ASA

### 3.3 Student → Vendor Spending

Spending is a **plain ASA transfer** (no smart contract call needed).
The student wallet app constructs the transaction and attaches a
JSON note field:

```json
{"cat": "food"}
```

Valid categories: `food`, `events`, `stationery`

This is enforced at the **application layer** — the vendor's QR code
includes the category, and the wallet app attaches it automatically.

---

## 4. Backend API Flow (Flask)

### 4.1 Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | — | Register student or parent |
| `/api/auth/login` | POST | — | Login, returns JWT |
| `/api/student/balance` | GET | Student | Get CAMPUS token balance |
| `/api/student/pay` | POST | Student | Pay a vendor (submits ASA txn) |
| `/api/parent/fund` | POST | Parent | Simulated UPI → mint tokens to child |
| `/api/parent/spending` | GET | Parent | **Aggregated** spending summary |
| `/api/vendor/register` | POST | Admin | Register vendor + category |
| `/api/vendor/qr` | GET | Vendor | Generate payment QR |

### 4.2 Funding Flow

```
Parent clicks "Add ₹500"
        │
        ▼
POST /api/parent/fund { amount: 500 }
        │
        ▼
Backend simulates UPI success
        │
        ▼
Backend signs Algorand txn:
  - Calls CampusVault.fund_student(student_addr, 500)
  - OR direct ASA transfer from admin → student
        │
        ▼
500 CAMPUS tokens land in student wallet
        │
        ▼
DB: INSERT INTO funding_log (parent_id, student_id, amount, timestamp)
```

### 4.3 Spending Indexer (Background Worker)

```python
# Runs every 30 seconds (or webhook-based)
while True:
    txns = algod_indexer.search_transactions(
        address=student_address,
        asset_id=campus_token_id,
        txn_type="axfer"
    )
    for txn in txns:
        if txn already processed:
            continue
        category = parse_note(txn.note)  # e.g. "food"
        amount = txn.asset_transfer.amount

        # AGGREGATE ONLY — no raw txn details stored for parent view
        db.execute("""
            INSERT INTO category_spending (student_id, category, month, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, category, month)
            DO UPDATE SET amount = amount + ?
        """, [student_id, category, current_month, amount, amount])

        db.execute("""
            INSERT INTO processed_txns (txn_id) VALUES (?)
        """, [txn.id])
```

### 4.4 Aggregation API Response

```
GET /api/parent/spending?student_id=123&month=2026-02

Response:
{
  "student_name": "Ameya",
  "month": "2026-02",
  "total_funded": 2000,
  "total_spent": 1500,
  "balance": 500,
  "breakdown": {
    "food": 700,
    "events": 500,
    "stationery": 300
  }
}
```

**What is returned:** Totals and category breakdown only.
**What is NOT returned:** Transaction hashes, merchant names, timestamps, individual amounts.

---

## 5. Parent Privacy Model

### The Problem

Algorand is a public blockchain. Any transaction from Student → Vendor is
visible on-chain: sender, receiver, amount, timestamp, note field.

If a parent had direct blockchain access, they could see:
- Exactly how much was spent at each vendor
- Exact timestamps of every purchase
- Vendor wallet addresses (which could be mapped to names)

### The Solution: Backend Aggregation Layer

The privacy model works by placing a **controlled backend layer** between
the blockchain and the parent's view:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Algorand    │────▶│   Backend    │────▶│   Parent     │
│  (raw txns)  │     │  (indexer +  │     │  Dashboard   │
│              │     │  aggregator) │     │  (summaries) │
└──────────────┘     └──────────────┘     └──────────────┘

   FULL DETAIL          PROCESSES           ONLY SEES:
   - txn hash           - reads txns        - total spent
   - sender/receiver    - maps vendor →     - per-category
   - amount               category          - balance
   - timestamp          - aggregates by
   - note field           category+month
                        - DISCARDS detail
                          from parent API
```

### Step-by-Step Privacy Flow

1. **Student pays vendor** — an ASA transfer with note `{"cat":"food"}`
   is submitted on-chain.

2. **Indexer reads the transaction** — the backend polls the Algorand
   Indexer API for new transactions involving the student's address.

3. **Category extraction** — the note field is parsed; OR the vendor
   address is looked up in the `vendor_registry` table to determine
   category. (Dual approach — note field is primary, vendor lookup is
   fallback.)

4. **Aggregation** — the backend adds the amount to the
   `category_spending` table: `food += 50`. No individual transaction
   record is stored in the parent-facing data model.

5. **Parent queries dashboard** — the API returns only the aggregated
   sums. The parent sees "Food: ₹700 this month" but never "₹50 at
   Canteen A at 2:34 PM".

### Why This Is Safe

| Threat | Mitigation |
|--------|------------|
| Parent reads blockchain directly | They would need the student's wallet address. The app never exposes it. The address is an opaque 58-char Algorand string. |
| Parent reverse-engineers the app | Even if they found the address, the blockchain shows `{"cat":"food"}` in the note — it does NOT show the vendor's real name. |
| Vendor addresses are traceable | For MVP scope, this is acceptable. In production, a mixer/relay contract could anonymize vendor addresses. |
| Backend operator leaks data | Access control + data minimization — the parent API physically cannot return what isn't in its response schema. |

### Privacy Summary

| Data Point | Student Sees | Parent Sees | On-Chain |
|------------|-------------|-------------|----------|
| Balance | ✅ | ✅ | ✅ |
| Total monthly spending | ✅ | ✅ | Derivable |
| Spending per category | ✅ | ✅ | Derivable |
| Individual transaction | ✅ | ❌ | ✅ |
| Merchant name | ✅ | ❌ | ❌ (only address) |
| Transaction time | ✅ | ❌ | ✅ |
| Transaction hash | ✅ | ❌ | ✅ |

---

## 6. Project Structure

```
escrow-smart-contract/
├── ARCHITECTURE.md          ← This document
├── README.md                ← Project overview & setup
├── contracts/
│   ├── create_asa.py        ← ASA creation script
│   ├── campus_vault.py      ← CampusVault PyTeal contract
│   ├── compile_contract.py  ← Compile PyTeal → TEAL
│   └── deploy.py            ← Deploy contract + bootstrap
├── backend/
│   ├── requirements.txt
│   ├── app.py               ← Flask API entry point
│   ├── config.py            ← Algorand connection config
│   ├── models.py            ← SQLite models
│   ├── routes/
│   │   ├── auth.py
│   │   ├── student.py
│   │   ├── parent.py
│   │   └── vendor.py
│   └── services/
│       ├── algorand_service.py  ← Algorand SDK wrappers
│       └── indexer_service.py   ← Spending indexer
└── frontend/
    └── (React app — scaffolded separately)
```

---

## 7. Tech Stack

| Layer | Technology |
|-------|-----------|
| Blockchain | Algorand Testnet |
| Smart Contracts | PyTeal |
| Token | ASA (Algorand Standard Asset) |
| Backend | Python, Flask, py-algorand-sdk |
| Database | SQLite (MVP) / PostgreSQL (prod) |
| Frontend | React (separate setup) |
| Auth | JWT |
| Deployment | Algorand Testnet via algonode.io |

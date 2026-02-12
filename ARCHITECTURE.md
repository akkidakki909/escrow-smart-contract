# CampusChain — Architecture & Design Document

> **Custodial Campus Wallet System on Algorand Testnet**
> No crypto knowledge required for any user.

---

## 1. High-Level Architecture (Custodial Model)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js + TypeScript)                │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │   Parent     │  │   Student   │  │  Vendor  │  │    Admin    │  │
│  │  Dashboard   │  │  Dashboard  │  │ Dashboard│  │  Dashboard  │  │
│  │  ─ Fund btn  │  │  ─ Balance  │  │ ─ Accept │  │  ─ Totals   │  │
│  │  ─ Category  │  │  ─ Spending │  │   payment│  │  ─ Category │  │
│  │    chart     │  │  ─ History  │  │ ─ Category│  │    stats    │  │
│  │  ─ NO txns   │  │             │  │          │  │             │  │
│  └──────┬───────┘  └──────┬──────┘  └────┬─────┘  └──────┬──────┘  │
└─────────┼─────────────────┼──────────────┼────────────────┼─────────┘
          │                 │              │                │
          ▼     REST API (JWT auth)        ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND API (Flask / Python)                    │
│                                                                     │
│  POST /parent/fund         POST /vendor/pay       GET /admin/stats  │
│  GET  /parent/spending     POST /vendor/register                    │
│  GET  /student/summary     GET  /student/balance                    │
│                                                                     │
│  ┌──────────────────────────────────────────────┐                  │
│  │  CUSTODIAL WALLET MANAGER                     │                  │
│  │  ─ Stores mnemonics in DB                     │                  │
│  │  ─ Signs ALL transactions server-side         │                  │
│  │  ─ Users never see or touch private keys      │                  │
│  └──────────────────────────────────────────────┘                  │
│                                                                     │
│  ┌──────────────────────────────────────────────┐                  │
│  │  PRIVACY AGGREGATION LAYER                    │                  │
│  │  ─ At payment time: upsert category_spending  │                  │
│  │  ─ Parent API returns ONLY aggregated sums    │                  │
│  │  ─ No individual txns, no vendor names,       │                  │
│  │    no timestamps in parent response           │                  │
│  └──────────────────────────────────────────────┘                  │
│                                                                     │
│  ┌───────────────── SQLite ──────────────────────┐                  │
│  │  users (+ algo_mnemonic)  │  vendors           │                  │
│  │  parent_student           │  category_spending  │                  │
│  │  funding_log              │  transactions       │                  │
│  └──────────────────────────────────────────────-┘                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │  py-algorand-sdk (signs txns)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ALGORAND TESTNET                                 │
│                                                                     │
│  CampusToken ASA  (1 token = ₹1, 0 decimals)                      │
│  Admin wallet     (holds reserve, funds students)                  │
│  Student wallets  (custodial — keys in backend DB)                 │
│  Vendor wallets   (custodial — receive payments)                   │
│                                                                     │
│  Txn note field:  {"cat":"food"} for on-chain traceability         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Custodial Funding Model

**Key Principle:** No user — parent, student, or vendor — ever needs cryptocurrency, 
a browser extension, or a wallet app.

### How It Works

| Step | Who | What Happens |
|------|-----|--------------|
| 1 | Parent | Clicks "Fund ₹500" in the web UI |
| 2 | Backend | Simulates UPI payment success |
| 3 | Backend | Signs an ASA transfer (admin → student) using admin's mnemonic from `.env` |
| 4 | Algorand | 500 CampusTokens land in the student's custodial wallet |
| 5 | Student | Buys food — vendor enters student ID + amount in vendor dashboard |
| 6 | Backend | Signs an ASA transfer (student → vendor) using student's mnemonic from DB |
| 7 | Backend | Records transaction + updates aggregated `category_spending` table |
| 8 | Parent | Sees "Food: ₹50" in monthly breakdown — never sees the vendor name or timestamp |

**Why custodial is safer for a hackathon MVP:**
- No wallet onboarding friction
- No lost private keys
- No student mnemonic exposure
- Parent never touches blockchain at all

---

## 3. Token Design — CampusToken (CAMPUS)

| Property | Value |
|----------|-------|
| Type | Algorand Standard Asset (ASA) |
| Unit Name | `CAMPUS` |
| Decimals | `0` (1 token = ₹1) |
| Total Supply | `1,000,000,000` |
| Manager/Reserve | Admin wallet |

---

## 4. Privacy Model

### What Each Role Sees

| Data Point | Parent | Student | Vendor | Admin | On-Chain |
|------------|--------|---------|--------|-------|----------|
| Balance | ✅ | ✅ | ✅ | ✅ | ✅ |
| Monthly total spending | ✅ | ✅ | — | ✅ | Derivable |
| Spending per category | ✅ | ✅ | — | ✅ | Derivable |
| Individual transactions | ❌ | ✅ | — | ✅ | ✅ |
| Merchant name | ❌ | ✅ | — | — | ❌ |
| Transaction timestamp | ❌ | ✅ | — | — | ✅ |

### How Aggregation Works (Without Exposing Raw Txns)

```
POST /vendor/pay  →  Backend signs ASA Transfer (student → vendor)
                 →  INSERT INTO transactions (student_id, vendor_id, amount, category)
                 →  UPSERT category_spending SET amount = amount + X
                        WHERE student_id = ? AND category = ? AND month = ?

GET /parent/spending  →  SELECT category, amount FROM category_spending
                     →  Returns: { "food": 700, "events": 500, "stationery": 300 }
                     →  Does NOT return individual rows from 'transactions' table
```

---

## 5. API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | — | Register (auto-creates custodial wallet) |
| `/api/auth/login` | POST | — | Login → JWT |
| `/api/auth/link-student` | POST | — | Link parent to student |
| `/api/parent/fund` | POST | Parent | Simulated UPI → mint tokens |
| `/api/parent/spending` | GET | Parent | Aggregated spending only |
| `/api/parent/students` | GET | Parent | List linked students |
| `/api/student/balance` | GET | Student | Token balance |
| `/api/student/summary` | GET | Student | Monthly spending + txn history |
| `/api/vendor/register` | POST | Vendor | Register + set category |
| `/api/vendor/pay` | POST | Vendor | Accept payment (backend-signed) |
| `/api/vendor/balance` | GET | Vendor | Token balance |
| `/api/vendor/qr` | GET | Vendor | Payment QR data |
| `/api/admin/stats` | GET | Admin | System-wide totals |

---

## 6. Project Structure

```
escrow-smart-contract/
├── ARCHITECTURE.md
├── README.md
├── .env.example
├── contracts/
│   ├── create_asa.py
│   ├── campus_vault.py
│   └── deploy.py
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── auth.py
│   │   ├── student.py
│   │   ├── parent.py
│   │   ├── vendor.py
│   │   └── admin.py
│   └── services/
│       └── algorand_service.py
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tsconfig.json
    └── src/
        ├── lib/api.ts
        └── app/
            ├── layout.tsx
            ├── globals.css
            ├── page.tsx          (Login/Register)
            ├── parent/page.tsx   (Parent Dashboard)
            ├── student/page.tsx  (Student Dashboard)
            ├── vendor/page.tsx   (Vendor Dashboard)
            └── admin/page.tsx    (Admin Dashboard)
```

# CampusChain 🎓⛓️

> Programmable Campus Wallet System on Algorand Testnet — **Custodial Model**

A hackathon MVP where students spend tokens at campus vendors and parents
see **only aggregated spending by category** — no crypto wallet required for anyone.

## Architecture

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the full design document.

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- An Algorand Testnet account funded via [faucet](https://bank.testnet.algorand.network/)

### 1. Setup

```bash
cp .env.example .env
# Edit .env — add your funded admin mnemonic, ASA_ID after creation
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

### 2. Create CampusToken ASA

```bash
python contracts/create_asa.py
# Copy the ASA ID into .env as ASA_ID=...
```

### 3. Run Backend

```bash
cd backend
python app.py
```

### 4. Run Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` → Register → Login → Dashboard.

## Custodial Model

**No user needs crypto.** The backend:
1. Creates Algorand wallets silently during registration
2. Stores private keys (mnemonics) server-side in the database
3. Signs every transaction (fund, spend) on behalf of users
4. Parents only click "Fund ₹500" — no wallet connect, no MetaMask, nothing

## Privacy Model

Parents see: ✅ Balance, ✅ Monthly total, ✅ Per-category breakdown

Parents don't see: ❌ Individual transactions, ❌ Merchant names, ❌ Timestamps

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | — | Register (auto wallet) |
| `/api/auth/login` | POST | — | Login → JWT |
| `/api/parent/fund` | POST | Parent | Fund student |
| `/api/parent/spending` | GET | Parent | Aggregated only |
| `/api/student/summary` | GET | Student | Spending + balance |
| `/api/vendor/pay` | POST | Vendor | Accept payment |
| `/api/admin/stats` | GET | Admin | System totals |

## Tech Stack

| Layer | Tech |
|-------|------|
| Blockchain | Algorand Testnet |
| Smart Contracts | PyTeal |
| Token | ASA (CampusToken) |
| Backend | Python, Flask, py-algorand-sdk |
| Frontend | Next.js 14, TypeScript |
| Database | SQLite |
| Auth | JWT |

## Team

Akshat Tripathi · Ameya Morgaonkar · Arnav Jakate · Ayush Andure

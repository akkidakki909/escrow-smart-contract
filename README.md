# CampusChain 

> Programmable Campus Wallet System on Algorand Testnet

A hackathon MVP that gives students a blockchain-powered campus wallet.
Parents fund it, students spend at vendors, and parents see **only aggregated
spending by category** — never individual transactions.

## Architecture

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the full design document.

```
contracts/       → PyTeal smart contracts + ASA creation
backend/         → Flask API (funding, payments, privacy-preserving aggregation)
frontend/        → (React app — scaffold separately)
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- An Algorand Testnet account funded via [faucet](https://bank.testnet.algorand.network/)

### 2. Install

```bash
pip install -r backend/requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your admin mnemonic
```

### 4. Create CampusToken (ASA)

```bash
python contracts/create_asa.py
```

### 5. Compile & Deploy CampusVault

```bash
python contracts/campus_vault.py    # Compiles PyTeal → TEAL
python contracts/deploy.py          # Deploys app + bootstraps
```

### 6. Run Backend

```bash
cd backend
python app.py
```

Server runs at `http://localhost:5000`.

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | — | Register (generates Algo wallet) |
| `/api/auth/login` | POST | — | Login → JWT |
| `/api/student/balance` | GET | Student | CampusToken balance |
| `/api/student/pay` | POST | Student | Pay vendor (category-tagged) |
| `/api/parent/fund` | POST | Parent | Simulate UPI → mint tokens |
| `/api/parent/spending` | GET | Parent | **Aggregated** spending only |
| `/api/vendor/register` | POST | Vendor | Register + set category |
| `/api/vendor/qr` | GET | Vendor | Payment QR data |

## Privacy Model

Parents see:
- Total monthly spending
- Spending per category (food, events, stationery)
- Remaining balance

Parents do NOT see:
- Individual transactions
- Merchant names
- Timestamps / time-level details

This is enforced by the **backend aggregation layer** — see `ARCHITECTURE.md` §5.

## Tech Stack

| Layer | Tech |
|-------|------|
| Blockchain | Algorand Testnet |
| Smart Contracts | PyTeal (TEAL v8) |
| Token | ASA (CampusToken) |
| Backend | Python, Flask, py-algorand-sdk |
| Database | SQLite |
| Auth | JWT |

## Team

Akshat Tripathi · Ameya Morgaonkar · Arnav Jakate · Ayush Andure

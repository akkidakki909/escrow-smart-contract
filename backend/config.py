"""
CampusChain Backend — Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Algorand
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")
INDEXER_ADDRESS = os.getenv("INDEXER_ADDRESS", "https://testnet-idx.algonode.cloud")
INDEXER_TOKEN = os.getenv("INDEXER_TOKEN", "")

ADMIN_MNEMONIC = os.getenv("ADMIN_MNEMONIC", "")
ASA_ID = int(os.getenv("ASA_ID", "0"))
APP_ID = int(os.getenv("APP_ID", "0"))

# Flask
SECRET_KEY = os.getenv("SECRET_KEY", "campuschain-dev-secret-key-change-in-prod")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "campuschain-jwt-secret")

# Database
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///campuschain.db")

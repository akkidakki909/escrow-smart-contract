"""
CampusChain Backend — Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Algorand
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")

ADMIN_MNEMONIC = os.getenv("ADMIN_MNEMONIC", "")
ASA_ID = int(os.getenv("ASA_ID", "0"))

# Flask
SECRET_KEY = os.getenv("SECRET_KEY", "campuschain-dev-secret-key-change-in-prod")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "campuschain-jwt-secret")

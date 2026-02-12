"""
Indexer service is no longer needed in the custodial model.

Spending aggregation is now done at payment time in routes/vendor.py
when the backend processes POST /vendor/pay. The category_spending
table is updated atomically alongside the transaction record.

This file is kept as a placeholder for documentation purposes.
"""

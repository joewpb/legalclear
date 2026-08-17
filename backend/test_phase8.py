import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inspect
from src.memory.db import DatabaseManager

methods = [
    "get_or_create_user", "update_user_subscription",
    "get_user", "mark_free_doc_used",
    "create_session", "update_payment_status",
    "get_session", "create_document", "save_results",
    "update_document_status", "get_document",
    "get_user_documents", "save_message",
    "get_history", "log_usage"
]

for method in methods:
    assert hasattr(DatabaseManager, method), (
        f"Missing method: {method}")
    print(f"  {method}: OK")

print("\nALL PHASE 8 STRUCTURAL CHECKS PASSED")
print("NOTE: Run SQL in Supabase dashboard before")
print("testing live database operations.")

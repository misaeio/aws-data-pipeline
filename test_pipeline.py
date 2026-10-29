import pytest
from lambda_function import validate_record

def test_validate_record_valid():
    sample = {
        "transaction_id": "TX1001",
        "customer_id": "CUST01",
        "amount": 150.50,
        "timestamp": "2026-10-27T10:00:00Z"
    }
    is_valid, reason = validate_record(sample)
    assert is_valid is True
    assert reason is None

def test_validate_record_negative_amount():
    sample = {
        "transaction_id": "TX1002",
        "customer_id": "CUST02",
        "amount": -45.00,
        "timestamp": "2026-10-27T10:05:00Z"
    }
    is_valid, reason = validate_record(sample)
    assert is_valid is False
    assert "Invalid amount" in reason

def test_validate_record_missing_field():
    sample = {
        "customer_id": "CUST03",
        "amount": 89.99,
        "timestamp": "2026-10-27T10:10:00Z"
    }
    is_valid, reason = validate_record(sample)
    assert is_valid is False
    assert "Missing required field: 'transaction_id'" in reason
    
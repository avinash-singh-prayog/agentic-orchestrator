{
  "transaction_master": {
    "transaction_id": "TXN-9845721934",
    "merchant_id": "MRC-102938",
    "merchant_name": "UrbanKart Pvt Ltd",
    "payment_method": "UPI",
    "payer_vpa": "rahul@okhdfcbank",
    "payee_vpa": "urbankart@hdfcbank",
    "bank": "HDFC Bank",
    "amount": 1249.00,
    "currency": "INR",
    "initiated_at": "2026-02-02T14:12:43+05:30",
    "authorization_status": "SUCCESS",
    "authorization_ref": "HDFCUPI783421",
    "current_status": "UNPROCESSED",
    "expected_settlement_date": "2026-02-02",
    "actual_settlement_date": null,
    "sla_breached": true,
    "transaction_age_hours": 26
  },
  "system_journey": [
    {
      "system": "INGESTION",
      "status": "SUCCESS",
      "event_id": "ING-778812",
      "timestamp": "2026-02-02T14:12:43+05:30"
    },
    {
      "system": "AUTH",
      "status": "SUCCESS",
      "bank_ref_id": "HDFCUPI783421",
      "rrn": "610214781245",
      "timestamp": "2026-02-02T14:12:45+05:30"
    },
    {
      "system": "ROUTER",
      "status": "SUCCESS",
      "route_selected": "UPI-HDFC",
      "switch_id": "SW-44921",
      "timestamp": "2026-02-02T14:12:46+05:30"
    },
    {
      "system": "LEDGER",
      "status": "PARTIAL_SUCCESS",
      "debit_entry": {
        "status": "POSTED",
        "entry_id": "LDG-DR-889134"
      },
      "credit_entry": {
        "status": "MISSING",
        "reason": "DB_TIMEOUT"
      },
      "timestamp": "2026-02-02T14:12:47+05:30"
    },
    {
      "system": "SETTLEMENT_ENGINE",
      "status": "NOT_TRIGGERED",
      "blocking_reason": "Ledger credit entry missing",
      "timestamp": "2026-02-02T14:30:00+05:30"
    },
    {
      "system": "BANK_FILE",
      "status": "SKIPPED",
      "dependency": "Settlement engine not completed"
    }
  ],
  "rca_analysis": {
    "rca_status": "COMPLETED",
    "root_cause_category": "SYNC_ISSUE",
    "root_cause": "Partial ledger write – credit entry missing",
    "failed_system": "LEDGER",
    "failure_type": "PARTIAL_WRITE",
    "first_failure_timestamp": "2026-02-02T14:12:47+05:30",
    "evidence": [
      "Debit entry exists in ledger",
      "Credit entry missing",
      "Settlement engine dependency unmet",
      "No bank file generated"
    ],
    "merchant_impact": "Settlement delayed",
    "risk_level": "LOW",
    "self_healable": true
  },
  "self_healing_action": {
    "action_id": "AUTO-HEAL-44211",
    "action_type": "LEDGER_RESYNC",
    "triggered_by": "AI_AGENT",
    "retry_count": 1,
    "result": "SUCCESS",
    "details": {
      "credit_entry_created": "LDG-CR-991204",
      "idempotency_key": "TXN-9845721934"
    },
    "timestamp": "2026-02-03T15:58:11+05:30"
  },
  "final_outcome": {
    "settlement_status": "SUCCESS",
    "bank_file_id": "HDFC-UPI-SETTLE-02032026-17",
    "settled_at": "2026-02-03T16:41:09+05:30",
    "final_status": "SETTLED"
  }
}

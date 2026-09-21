from datetime import datetime
import hashlib

DEMO_KYC = {
    "0x1111111111111111111111111111111111111111": {
        "vasp_name": "Demo Exchange Alpha",
        "customer_reference": "DEMO-KYC-001",
        "account_holder": "Demo Subject A",
        "kyc_status": "Verified (synthetic demo)",
        "country": "India (demo)",
        "phone": "+91-98******21",
        "email": "subject.a***@example.demo",
        "account_created": "2025-11-18",
        "linked_wallets": ["DEMO_SUSPECT_A"],
        "source": "Synthetic VASP KYC response for hackathon demonstration"
    },
    "0x2222222222222222222222222222222222222222": {
        "vasp_name": "Demo Exchange Beta",
        "customer_reference": "DEMO-KYC-002",
        "account_holder": "Demo Subject B",
        "kyc_status": "Verified (synthetic demo)",
        "country": "India (demo)",
        "phone": "+91-97******44",
        "email": "subject.b***@example.demo",
        "account_created": "2026-01-09",
        "linked_wallets": ["DEMO_SUSPECT_A"],
        "source": "Synthetic VASP KYC response for hackathon demonstration"
    }
}


def build_case_evidence(case):
    return {
        "case_id": case.get("case_id", ""),
        "reported_wallet": case.get("wallet", ""),
        "blockchain": case.get("blockchain", ""),
        "risk_score": case.get("risk_score", 0),
        "risk_level": case.get("risk_level", ""),
        "vasp": case.get("vasp", {}),
        "transaction_count": len(case.get("transactions", [])),
        "evidence_hash": evidence_hash(case),
    }


def evidence_hash(case):
    raw = repr({
        "case_id": case.get("case_id"),
        "wallet": case.get("wallet"),
        "transactions": case.get("transactions", []),
        "vasp": case.get("vasp", {}),
    }).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def prepare_request(case, request_type="KYC / Account Information Request"):
    evidence = build_case_evidence(case)
    return {
        "request_id": "REQ-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "status": "DRAFT",
        "request_type": request_type,
        "case_id": case.get("case_id", ""),
        "vasp_name": case.get("vasp", {}).get("name", ""),
        "vasp_address": case.get("vasp", {}).get("address", ""),
        "purpose": "Request relevant customer/account information connected to the identified blockchain endpoint for an authorized cyber-fraud investigation.",
        "requested_fields": [
            "Customer/account reference",
            "KYC verification status",
            "Account creation date",
            "Registered identity details, subject to applicable legal authority",
            "Registered contact details, subject to applicable legal authority",
            "Wallet/account linkage information relevant to the reported address",
            "Relevant account transaction records and preservation information"
        ],
        "evidence": evidence,
        "human_review": False,
        "authorized_submission": False,
        "prepared_at": datetime.now().isoformat(timespec="seconds")
    }


def mark_human_review(request):
    request = dict(request)
    request["human_review"] = True
    request["status"] = "READY_FOR_AUTHORIZATION"
    request["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    return request


def authorize_submission(request):
    request = dict(request)
    if not request.get("human_review"):
        raise ValueError("Human investigator review is required before authorization.")
    request["authorized_submission"] = True
    request["status"] = "AUTHORIZED_FOR_SUBMISSION"
    request["authorized_at"] = datetime.now().isoformat(timespec="seconds")
    return request


def simulate_vasp_response(request):
    if not request.get("authorized_submission"):
        raise ValueError("The request must be authorized before a demo response is generated.")
    address = request.get("vasp_address", "").lower()
    response = DEMO_KYC.get(address)
    if not response:
        return {
            "status": "NO_DEMO_RESPONSE",
            "message": "No synthetic KYC response is configured for this VASP.",
            "request_id": request.get("request_id")
        }
    return {
        "status": "RESPONSE_RECEIVED",
        "request_id": request.get("request_id"),
        "received_at": datetime.now().isoformat(timespec="seconds"),
        **response
    }

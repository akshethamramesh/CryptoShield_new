import json
import os
from typing import Any, Dict, List, Optional


LABEL_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "exchange_labels.json"
)


def normalize_address(address: Any) -> str:
    """
    Normalize an Ethereum-style address for reliable comparison.
    """
    if not address:
        return ""

    return str(address).strip().lower()


def load_exchange_labels(
    labels_file: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Load the curated VASP/exchange address registry.
    """

    path = labels_file or LABEL_FILE

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, dict):
            return {}

        normalized = {}

        for address, info in raw.items():

            normalized_address = normalize_address(address)

            if not normalized_address:
                continue

            if not isinstance(info, dict):
                continue

            normalized[normalized_address] = info

        return normalized

    except FileNotFoundError:
        return {}

    except json.JSONDecodeError:
        return {}


def _extract_addresses_from_transaction(tx: Dict[str, Any]) -> List[str]:
    """
    Extract possible wallet addresses from a transaction.

    Supports different field names because live blockchain APIs
    may return slightly different structures.
    """

    addresses = []

    possible_fields = [
        "from",
        "to",
        "from_address",
        "to_address",
        "sender",
        "receiver",
        "wallet",
        "address"
    ]

    for field in possible_fields:

        value = tx.get(field)

        if isinstance(value, str) and value.strip():
            addresses.append(value)

    # Some transaction structures may contain nested address objects.
    for field in ["from", "to"]:

        value = tx.get(field)

        if isinstance(value, dict):

            for nested_field in ["address", "hash", "value"]:

                nested_value = value.get(nested_field)

                if isinstance(nested_value, str):
                    addresses.append(nested_value)

    return addresses


def _get_transaction_hop(
    tx: Dict[str, Any],
    start_wallet: str = ""
) -> Optional[int]:

    for field in [
        "hop",
        "wallet_hop",
        "depth",
        "trace_depth",
        "max_hop"
    ]:

        value = tx.get(field)

        if isinstance(value, int):
            return value

        if isinstance(value, str):

            try:
                return int(value)

            except ValueError:
                pass

    return None


def detect_known_vasps(
    transactions: List[Dict[str, Any]],
    start_wallet: str = "",
    labels_file: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Detect known VASP/exchange endpoints from:

    1. The reported wallet itself
    2. Transaction sender addresses
    3. Transaction receiver addresses

    Matching is case-insensitive.

    IMPORTANT:
    This does NOT prove ownership of an individual or account.
    It only identifies an address that matches the curated
    public VASP/exchange registry.
    """

    labels = load_exchange_labels(labels_file)

    if not labels:
        return []

    start = normalize_address(start_wallet)

    results = {}

    # ---------------------------------------------------------
    # 1. CHECK THE REPORTED WALLET ITSELF
    # ---------------------------------------------------------

    if start and start in labels:

        info = labels[start]

        results[start] = {
            "address": start,
            "name": info.get("name", "Unknown VASP"),
            "type": info.get(
                "type",
                "Centralized Exchange / VASP"
            ),
            "country": info.get(
                "country",
                "Unknown"
            ),
            "source": info.get(
                "label_source",
                "CryptoShield VASP Registry"
            ),
            "role": "Reported wallet",
            "hop": 0,
            "confidence": "High",
            "evidence": (
                "The reported wallet directly matches "
                "a curated VASP/exchange address."
            ),
            "kyc_note": (
                "Any identity or account information must be "
                "requested from the VASP through applicable "
                "authority and legal process."
            )
        }

    # ---------------------------------------------------------
    # 2. CHECK TRANSACTION PARTICIPANTS
    # ---------------------------------------------------------

    for tx in transactions or []:

        tx_addresses = _extract_addresses_from_transaction(tx)

        hop = _get_transaction_hop(
            tx,
            start_wallet=start_wallet
        )

        tx_hash = (
            tx.get("hash")
            or tx.get("tx_hash")
            or tx.get("transaction_hash")
            or ""
        )

        for address in tx_addresses:

            normalized = normalize_address(address)

            if not normalized:
                continue

            if normalized not in labels:
                continue

            info = labels[normalized]

            # Don't overwrite a stronger/root match.
            if normalized in results:
                continue

            results[normalized] = {
                "address": normalized,
                "name": info.get(
                    "name",
                    "Unknown VASP"
                ),
                "type": info.get(
                    "type",
                    "Centralized Exchange / VASP"
                ),
                "country": info.get(
                    "country",
                    "Unknown"
                ),
                "source": info.get(
                    "label_source",
                    "CryptoShield VASP Registry"
                ),
                "role": "Transaction participant",
                "hop": hop,
                "confidence": "High",
                "evidence": (
                    "A transaction participant matches "
                    "a curated VASP/exchange address."
                ),
                "transaction_hash": tx_hash,
                "kyc_note": (
                    "Any identity or account information must be "
                    "requested from the VASP through applicable "
                    "authority and legal process."
                )
            }

    return list(results.values())


def find_vasp_for_wallet(
    wallet_address: str,
    labels_file: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Directly check whether one wallet is present in the
    curated VASP registry.
    """

    labels = load_exchange_labels(labels_file)

    normalized = normalize_address(wallet_address)

    if not normalized:
        return None

    info = labels.get(normalized)

    if not info:
        return None

    return {
        "address": normalized,
        "name": info.get(
            "name",
            "Unknown VASP"
        ),
        "type": info.get(
            "type",
            "Centralized Exchange / VASP"
        ),
        "country": info.get(
            "country",
            "Unknown"
        ),
        "source": info.get(
            "label_source",
            "CryptoShield VASP Registry"
        ),
        "role": "Direct wallet match",
        "hop": 0,
        "confidence": "High",
        "evidence": (
            "Wallet directly matches the curated "
            "VASP/exchange registry."
        )
    }


def get_vasp_summary(
    vasps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create a simple summary for the Streamlit UI.
    """

    if not vasps:

        return {
            "found": False,
            "count": 0,
            "primary": None,
            "message": (
                "No known VASP endpoint was found "
                "in the current public attribution registry."
            )
        }

    # Prefer direct reported-wallet match.
    direct_matches = [
        v for v in vasps
        if v.get("hop") == 0
    ]

    primary = (
        direct_matches[0]
        if direct_matches
        else vasps[0]
    )

    return {
        "found": True,
        "count": len(vasps),
        "primary": primary,
        "message": (
            f"Known VASP endpoint identified: "
            f"{primary.get('name', 'Unknown')}"
        )
    }


def explain_vasp_match(
    vasp: Dict[str, Any]
) -> str:
    """
    Human-readable explanation for the UI.
    """

    name = vasp.get("name", "Unknown VASP")
    address = vasp.get("address", "")
    source = vasp.get("source", "Registry")
    hop = vasp.get("hop")

    if hop is None:
        hop_text = "Unknown"
    else:
        hop_text = str(hop)

    return (
        f"{name} was identified because address "
        f"{address} matches the CryptoShield VASP registry. "
        f"Trace hop: {hop_text}. "
        f"Attribution source: {source}. "
        f"This is an investigative endpoint attribution, "
        f"not proof of a person's identity or ownership."
    )

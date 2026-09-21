import json
import os
from collections import Counter


# ============================================================
# CRYPTOSHIELD - EXCHANGE INTELLIGENCE
# ============================================================
#
# Identifies potential exchange/VASP associations using
# labelled blockchain addresses.
#
# IMPORTANT:
# A label is NOT proof of ownership or criminal activity.
# Results are analytical investigation leads.
#
# ============================================================


DEFAULT_LABEL_FILE = "exchange_labels.json"


# ============================================================
# HELPERS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def safe_int(value):

    try:
        return int(value)

    except Exception:
        return 0


def safe_float(value):

    try:
        return float(value)

    except Exception:
        return 0.0


# ============================================================
# LOAD EXCHANGE LABELS
# ============================================================

def load_exchange_labels(
    label_file=None
):

    file_path = (
        label_file
        or DEFAULT_LABEL_FILE
    )


    # --------------------------------------------------------
    # If custom file exists
    # --------------------------------------------------------

    if os.path.exists(
        file_path
    ):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )


            if isinstance(
                data,
                dict
            ):

                return data


        except Exception:

            pass


    # --------------------------------------------------------
    # Demo fallback
    # --------------------------------------------------------

    return {

        "0x1111111111111111111111111111111111111111":
            {
                "name": "Demo Exchange Alpha",
                "type": "Centralized Exchange",
                "country": "Demo",
                "source": "CryptoShield Demo Registry"
            },

        "0x2222222222222222222222222222222222222222":
            {
                "name": "Demo Exchange Beta",
                "type": "Centralized Exchange",
                "country": "Demo",
                "source": "CryptoShield Demo Registry"
            },

        "0x3333333333333333333333333333333333333333":
            {
                "name": "Demo VASP Gamma",
                "type": "VASP",
                "country": "Demo",
                "source": "CryptoShield Demo Registry"
            }

    }


# ============================================================
# NORMALIZE LABELS
# ============================================================

def normalize_labels(
    labels
):

    normalized = {}


    if not isinstance(
        labels,
        dict
    ):

        return normalized


    for address, details in labels.items():

        address = normalize_address(
            address
        )


        if not address:

            continue


        if isinstance(
            details,
            str
        ):

            details = {
                "name": details
            }


        if not isinstance(
            details,
            dict
        ):

            details = {}


        normalized[address] = details


    return normalized


# ============================================================
# EXTRACT PARTICIPANTS
# ============================================================

def extract_transaction_participants(
    transactions
):

    participants = set()


    for tx in transactions:

        sender = normalize_address(
            tx.get(
                "from",
                ""
            )
        )

        receiver = normalize_address(
            tx.get(
                "to",
                ""
            )
        )


        if sender:

            participants.add(
                sender
            )


        if receiver:

            participants.add(
                receiver
            )


    return participants


# ============================================================
# FIND HOP
# ============================================================

def find_hop(
    address,
    transactions,
    wallet_hops=None
):

    address = normalize_address(
        address
    )


    # --------------------------------------------------------
    # Explicit wallet hop map
    # --------------------------------------------------------

    if isinstance(
        wallet_hops,
        dict
    ):

        value = wallet_hops.get(
            address
        )


        if value is not None:

            try:

                return int(
                    value
                )

            except Exception:

                pass


    # --------------------------------------------------------
    # Transaction metadata
    # --------------------------------------------------------

    detected_hops = []


    for tx in transactions:

        sender = normalize_address(
            tx.get(
                "from",
                ""
            )
        )

        receiver = normalize_address(
            tx.get(
                "to",
                ""
            )
        )


        if (
            sender == address
            or receiver == address
        ):

            hop = tx.get(
                "hop"
            )


            if hop is not None:

                try:

                    detected_hops.append(
                        int(hop)
                    )

                except Exception:

                    pass


    if detected_hops:

        return min(
            detected_hops
        )


    return None


# ============================================================
# TRANSACTION ROLE
# ============================================================

def get_exchange_role(
    address,
    transactions
):

    address = normalize_address(
        address
    )


    incoming = 0
    outgoing = 0

    incoming_volume = 0.0
    outgoing_volume = 0.0


    for tx in transactions:

        sender = normalize_address(
            tx.get(
                "from",
                ""
            )
        )

        receiver = normalize_address(
            tx.get(
                "to",
                ""
            )
        )

        value = safe_float(
            tx.get(
                "value",
                0
            )
        )


        if receiver == address:

            incoming += 1
            incoming_volume += value


        if sender == address:

            outgoing += 1
            outgoing_volume += value


    if incoming > 0 and outgoing > 0:

        role = "Sender + Receiver"

    elif incoming > 0:

        role = "Receiver"

    elif outgoing > 0:

        role = "Sender"

    else:

        role = "Participant"


    return {

        "role":
            role,

        "incoming_transactions":
            incoming,

        "outgoing_transactions":
            outgoing,

        "incoming_volume":
            incoming_volume,

        "outgoing_volume":
            outgoing_volume

    }


# ============================================================
# CHECK EXCHANGE ASSOCIATIONS
# ============================================================

def check_exchange_associations(
    transactions,
    wallet_hops=None,
    label_file=None
):

    if not transactions:

        return []


    labels = load_exchange_labels(
        label_file
    )


    labels = normalize_labels(
        labels
    )


    participants = (
        extract_transaction_participants(
            transactions
        )
    )


    associations = []


    for address in participants:

        if address not in labels:

            continue


        details = labels.get(
            address,
            {}
        )


        role_data = get_exchange_role(
            address,
            transactions
        )


        hop = find_hop(
            address,
            transactions,
            wallet_hops
        )


        name = details.get(
            "name",
            "Unknown Exchange/VASP"
        )


        entity_type = details.get(
            "type",
            "Exchange/VASP"
        )


        country = details.get(
            "country",
            "Unknown"
        )


        source = details.get(
            "source",
            "Unknown"
        )


        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        evidence = [

            "Address participated in traced transactions",

            "Address matched a labelled exchange/VASP registry entry"

        ]


        if hop is not None:

            evidence.append(
                f"Observed at hop {hop}"
            )


        if role_data[
            "incoming_transactions"
        ] > 0:

            evidence.append(
                "Received funds in analysed flow"
            )


        if role_data[
            "outgoing_transactions"
        ] > 0:

            evidence.append(
                "Sent funds in analysed flow"
            )


        association = {

            "address":
                address,

            "name":
                name,

            "type":
                entity_type,

            "country":
                country,

            "source":
                source,

            "hop":
                hop,

            "role":
                role_data[
                    "role"
                ],

            "incoming_transactions":
                role_data[
                    "incoming_transactions"
                ],

            "outgoing_transactions":
                role_data[
                    "outgoing_transactions"
                ],

            "incoming_volume":
                role_data[
                    "incoming_volume"
                ],

            "outgoing_volume":
                role_data[
                    "outgoing_volume"
                ],

            "association":
                "Potential exchange/VASP association",

            "confidence":
                "Analytical lead",

            "evidence":
                evidence,

            "kyc_investigation_lead":
                (
                    "If this endpoint is relevant to the investigation, "
                    "an authorized investigator may use applicable legal "
                    "procedures to request off-chain account/KYC information."
                ),

            "warning":
                (
                    "Label matching does not independently prove ownership, "
                    "control, fraud, or criminal activity."
                )

        }


        associations.append(
            association
        )


    # --------------------------------------------------------
    # Sort by hop
    # --------------------------------------------------------

    associations.sort(

        key=lambda item: (

            item.get(
                "hop"
            )
            if item.get(
                "hop"
            ) is not None
            else 999,

            item.get(
                "name",
                ""
            )

        )

    )


    return associations


# ============================================================
# SUMMARIZE EXCHANGE ASSOCIATIONS
# ============================================================

def summarize_exchange_associations(
    associations
):

    if not associations:

        return {

            "found":
                False,

            "count":
                0,

            "exchanges":
                [],

            "potential_endpoints":
                [],

            "message":
                (
                    "No labelled exchange/VASP endpoint "
                    "was detected in the analysed flow."
                )

        }


    exchanges = []

    endpoint_hops = []

    types = []


    for item in associations:

        name = item.get(
            "name"
        )


        if (
            name
            and name not in exchanges
        ):

            exchanges.append(
                name
            )


        hop = item.get(
            "hop"
        )


        if hop is not None:

            endpoint_hops.append(
                hop
            )


        entity_type = item.get(
            "type"
        )


        if (
            entity_type
            and entity_type not in types
        ):

            types.append(
                entity_type
            )


    return {

        "found":
            True,

        "count":
            len(associations),

        "exchanges":
            exchanges,

        "potential_endpoints":
            exchanges,

        "endpoint_hops":
            endpoint_hops,

        "types":
            types,

        "message":
            (
                "Potential exchange/VASP endpoint(s) detected "
                "from labelled blockchain addresses."
            )

    }


# ============================================================
# INVESTIGATION LEAD
# ============================================================

def build_investigation_leads(
    associations
):

    leads = []


    for item in associations:

        lead = {

            "endpoint":
                item.get(
                    "name",
                    "Unknown"
                ),

            "address":
                item.get(
                    "address",
                    ""
                ),

            "hop":
                item.get(
                    "hop"
                ),

            "role":
                item.get(
                    "role",
                    "Unknown"
                ),

            "reason":
                (
                    "Potential VASP/exchange endpoint "
                    "observed in traced fund flow."
                ),

            "next_step":
                (
                    "Authorized investigator may review the "
                    "on-chain evidence and follow applicable "
                    "legal procedures for off-chain records."
                )

        }


        leads.append(
            lead
        )


    return leads


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def check_exchange(
    transactions,
    wallet_hops=None
):

    return check_exchange_associations(
        transactions,
        wallet_hops=wallet_hops
    )


def detect_exchange(
    transactions,
    wallet_hops=None
):

    return check_exchange_associations(
        transactions,
        wallet_hops=wallet_hops
    )

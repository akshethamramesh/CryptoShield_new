import json
import os


# ============================================================
# CRYPTOSHIELD - VASP DETECTION
# ============================================================
#
# Detects potential associations between traced blockchain
# addresses and known / labelled VASP addresses.
#
# IMPORTANT:
# A blockchain address label is an analytical indicator.
# It does NOT prove ownership, control, or criminal activity.
#
# ============================================================


# ------------------------------------------------------------
# Default demo registry
# ------------------------------------------------------------

VASP_REGISTRY = {

    # Demo addresses only.
    # Replace / extend these with properly sourced labels.

    "0x1111111111111111111111111111111111111111": {
        "name": "Demo Exchange Alpha",
        "type": "Centralized Exchange",
        "country": "Demo",
        "source": "CryptoShield Demo Registry"
    },

    "0x2222222222222222222222222222222222222222": {
        "name": "Demo Exchange Beta",
        "type": "Centralized Exchange",
        "country": "Demo",
        "source": "CryptoShield Demo Registry"
    },

    "0x3333333333333333333333333333333333333333": {
        "name": "Demo VASP Gamma",
        "type": "VASP",
        "country": "Demo",
        "source": "CryptoShield Demo Registry"
    }

}


# ============================================================
# HELPERS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def load_registry(
    registry=None,
    registry_file=None
):

    # --------------------------------------------------------
    # Custom registry supplied directly
    # --------------------------------------------------------

    if isinstance(
        registry,
        dict
    ):

        return {

            normalize_address(
                address
            ): details

            for address, details
            in registry.items()

        }


    # --------------------------------------------------------
    # Load external JSON registry
    # --------------------------------------------------------

    if registry_file:

        try:

            if os.path.exists(
                registry_file
            ):

                with open(
                    registry_file,
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

                    return {

                        normalize_address(
                            address
                        ): details

                        for address, details
                        in data.items()

                    }

        except Exception:

            pass


    # --------------------------------------------------------
    # Default registry
    # --------------------------------------------------------

    return VASP_REGISTRY.copy()


# ============================================================
# TRANSACTION PARTICIPANTS
# ============================================================

def extract_participants(
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
# GET TRANSACTION ROLE
# ============================================================

def get_transaction_role(
    address,
    transactions
):

    address = normalize_address(
        address
    )


    incoming = 0
    outgoing = 0


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


        if receiver == address:

            incoming += 1


        if sender == address:

            outgoing += 1


    if incoming > 0 and outgoing > 0:

        return "Sender + Receiver"

    if incoming > 0:

        return "Receiver"

    if outgoing > 0:

        return "Sender"


    return "Participant"


# ============================================================
# FIND HOP
# ============================================================

def find_address_hop(
    address,
    transactions,
    wallet_hops=None
):

    address = normalize_address(
        address
    )


    # --------------------------------------------------------
    # Use supplied hop information
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
    # Try transaction metadata
    # --------------------------------------------------------

    hops = []


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


        if sender == address:

            if tx.get(
                "hop"
            ) is not None:

                hops.append(
                    tx.get(
                        "hop"
                    )
                )


        if receiver == address:

            if tx.get(
                "hop"
            ) is not None:

                hops.append(
                    tx.get(
                        "hop"
                    )
                )


    if hops:

        try:

            return min(
                int(hop)
                for hop in hops
            )

        except Exception:

            pass


    return None


# ============================================================
# MATCH VASP ADDRESSES
# ============================================================

def detect_vasp(
    transactions,
    wallet_hops=None,
    registry=None,
    registry_file=None
):

    if not transactions:

        return []


    registry = load_registry(
        registry=registry,
        registry_file=registry_file
    )


    participants = (
        extract_participants(
            transactions
        )
    )


    matches = []


    for address in participants:

        if address not in registry:

            continue


        details = registry.get(
            address,
            {}
        )


        if not isinstance(
            details,
            dict
        ):

            details = {}


        hop = find_address_hop(
            address,
            transactions,
            wallet_hops
        )


        role = get_transaction_role(
            address,
            transactions
        )


        match = {

            "address":
                address,

            "name":
                details.get(
                    "name",
                    "Unknown VASP"
                ),

            "type":
                details.get(
                    "type",
                    "VASP"
                ),

            "country":
                details.get(
                    "country",
                    "Unknown"
                ),

            "source":
                details.get(
                    "source",
                    "Unknown"
                ),

            "role":
                role,

            "hop":
                hop,

            "confidence":
                "Potential association",

            "evidence":
                "Traced transaction participant matched a labelled VASP address",

            "kyc_note":
                (
                    "The VASP may hold off-chain customer information. "
                    "Authorized investigators can follow applicable legal "
                    "procedures to request relevant KYC/account information."
                )

        }


        matches.append(
            match
        )


    # --------------------------------------------------------
    # Sort by hop
    # --------------------------------------------------------

    matches.sort(

        key=lambda item: (
            item.get(
                "hop"
            )
            if item.get(
                "hop"
            ) is not None
            else 999
        )

    )


    return matches


# ============================================================
# VASP SUMMARY
# ============================================================

def summarize_vasp(
    matches
):

    if not matches:

        return {

            "found":
                False,

            "count":
                0,

            "vasps":
                [],

            "message":
                (
                    "No labelled VASP association was found "
                    "in the analysed transaction set."
                )

        }


    names = []

    types = []

    countries = []


    for item in matches:

        name = item.get(
            "name"
        )

        vasp_type = item.get(
            "type"
        )

        country = item.get(
            "country"
        )


        if name and name not in names:

            names.append(
                name
            )


        if (
            vasp_type
            and vasp_type not in types
        ):

            types.append(
                vasp_type
            )


        if (
            country
            and country not in countries
        ):

            countries.append(
                country
            )


    return {

        "found":
            True,

        "count":
            len(matches),

        "vasps":
            names,

        "types":
            types,

        "countries":
            countries,

        "message":
            (
                "Potential VASP association detected "
                "from labelled blockchain address participation."
            )

    }


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def detect_vasp_association(
    transactions,
    wallet_hops=None
):

    return detect_vasp(
        transactions,
        wallet_hops=wallet_hops
    )


def find_vasp(
    transactions
):

    return detect_vasp(
        transactions
    )

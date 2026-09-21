from collections import defaultdict
import networkx as nx


# ============================================================
# CRYPTOSHIELD - CROSS-CASE CONVERGENCE DETECTION
# ============================================================
#
# Compares multiple investigation cases and identifies:
#
# 1. Shared intermediary wallets
# 2. Shared final destinations
# 3. Possible fund-flow convergence
# 4. Potential fraud-ring clusters
#
# IMPORTANT:
# Shared wallets/destinations do NOT prove fraud or common
# ownership. They are investigation leads only.
#
# ============================================================


# ============================================================
# HELPERS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def safe_list(value):

    if value is None:

        return []

    if isinstance(
        value,
        list
    ):

        return value

    if isinstance(
        value,
        tuple
    ):

        return list(value)

    return [value]


# ============================================================
# EXTRACT WALLET SET
# ============================================================

def extract_wallets(case):

    wallets = set()


    important_wallets = safe_list(
        case.get(
            "important_wallets",
            []
        )
    )


    for wallet in important_wallets:

        if isinstance(
            wallet,
            dict
        ):

            address = wallet.get(
                "address"
            )

        else:

            address = wallet


        address = normalize_address(
            address
        )


        if address:

            wallets.add(
                address
            )


    # --------------------------------------------------------
    # Include original reported wallet
    # --------------------------------------------------------

    reported_wallet = normalize_address(
        case.get(
            "wallet_address",
            ""
        )
    )


    if reported_wallet:

        wallets.add(
            reported_wallet
        )


    return wallets


# ============================================================
# EXTRACT FINAL DESTINATIONS
# ============================================================

def extract_final_destinations(
    case
):

    destinations = set()


    values = safe_list(
        case.get(
            "final_destinations",
            []
        )
    )


    for item in values:

        if isinstance(
            item,
            dict
        ):

            address = (
                item.get(
                    "address"
                )
                or
                item.get(
                    "destination"
                )
                or
                item.get(
                    "wallet"
                )
            )

        else:

            address = item


        address = normalize_address(
            address
        )


        if address:

            destinations.add(
                address
            )


    return destinations


# ============================================================
# EXTRACT HOP PATH WALLETS
# ============================================================

def extract_path_wallets(
    case
):

    wallets = set()


    paths = safe_list(
        case.get(
            "hop_paths",
            []
        )
    )


    for path in paths:

        if isinstance(
            path,
            list
        ):

            for address in path:

                if isinstance(
                    address,
                    dict
                ):

                    address = (
                        address.get(
                            "address"
                        )
                        or
                        address.get(
                            "wallet"
                        )
                    )


                address = normalize_address(
                    address
                )


                if address:

                    wallets.add(
                        address
                    )


        elif isinstance(
            path,
            dict
        ):

            for key in (
                "from",
                "to",
                "address",
                "wallet"
            ):

                address = normalize_address(
                    path.get(
                        key,
                        ""
                    )
                )


                if address:

                    wallets.add(
                        address
                    )


    return wallets


# ============================================================
# BUILD CASE FINGERPRINT
# ============================================================

def build_case_fingerprint(
    case
):

    wallets = (
        extract_wallets(
            case
        )
    )


    path_wallets = (
        extract_path_wallets(
            case
        )
    )


    destinations = (
        extract_final_destinations(
            case
        )
    )


    wallets.update(
        path_wallets
    )


    return {

        "case_id":
            case.get(
                "case_id",
                "UNKNOWN"
            ),

        "reported_wallet":
            normalize_address(
                case.get(
                    "wallet_address",
                    ""
                )
            ),

        "wallets":
            wallets,

        "destinations":
            destinations

    }


# ============================================================
# COMPARE TWO CASES
# ============================================================

def compare_cases(
    case_a,
    case_b
):

    fingerprint_a = (
        build_case_fingerprint(
            case_a
        )
    )


    fingerprint_b = (
        build_case_fingerprint(
            case_b
        )
    )


    shared_wallets = (
        fingerprint_a[
            "wallets"
        ]
        &
        fingerprint_b[
            "wallets"
        ]
    )


    shared_destinations = (
        fingerprint_a[
            "destinations"
        ]
        &
        fingerprint_b[
            "destinations"
        ]
    )


    # Remove original reported wallets from
    # intermediary-wallet interpretation.

    shared_intermediaries = (
        shared_wallets
        -
        {
            fingerprint_a[
                "reported_wallet"
            ],
            fingerprint_b[
                "reported_wallet"
            ]
        }
    )


    connection_count = (
        len(
            shared_intermediaries
        )
        +
        len(
            shared_destinations
        )
    )


    # --------------------------------------------------------
    # Determine relationship
    # --------------------------------------------------------

    if (
        shared_destinations
        and shared_intermediaries
    ):

        relationship = (
            "Shared destination and intermediary"
        )

        severity = "HIGH"


    elif shared_destinations:

        relationship = (
            "Shared final destination"
        )

        severity = "HIGH"


    elif shared_intermediaries:

        relationship = (
            "Shared intermediary wallet"
        )

        severity = "MEDIUM"


    else:

        relationship = "No significant overlap detected"

        severity = "NONE"


    return {

        "case_a":
            fingerprint_a[
                "case_id"
            ],

        "case_b":
            fingerprint_b[
                "case_id"
            ],

        "shared_wallets":
            sorted(
                shared_intermediaries
            ),

        "shared_destinations":
            sorted(
                shared_destinations
            ),

        "relationship":
            relationship,

        "severity":
            severity,

        "connection_count":
            connection_count,

        "investigation_note":
            (
                "Shared blockchain entities indicate a potential "
                "cross-case connection. They do not independently "
                "prove common ownership or criminal activity."
            )

    }


# ============================================================
# DETECT CROSS-CASE CONVERGENCE
# ============================================================

def detect_cross_case_convergence(
    current_case,
    previous_cases
):

    if not current_case:

        return []


    if not previous_cases:

        return []


    results = []


    for previous_case in previous_cases:

        if not isinstance(
            previous_case,
            dict
        ):

            continue


        result = compare_cases(
            current_case,
            previous_case
        )


        if result[
            "severity"
        ] != "NONE":

            results.append(
                result
            )


    # --------------------------------------------------------
    # Strongest connections first
    # --------------------------------------------------------

    severity_rank = {

        "HIGH": 0,

        "MEDIUM": 1,

        "NONE": 2

    }


    results.sort(

        key=lambda item:
            (
                severity_rank.get(
                    item.get(
                        "severity",
                        "NONE"
                    ),
                    99
                ),

                -item.get(
                    "connection_count",
                    0
                )

            )

    )


    return results


# ============================================================
# BUILD ENTITY CONNECTION GRAPH
# ============================================================

def build_fraud_ring_clusters(
    cases
):

    graph = nx.Graph()


    fingerprints = []


    for case in cases:

        if not isinstance(
            case,
            dict
        ):

            continue


        fingerprints.append(
            build_case_fingerprint(
                case
            )
        )


    # --------------------------------------------------------
    # Case nodes
    # --------------------------------------------------------

    for fingerprint in fingerprints:

        case_id = fingerprint[
            "case_id"
        ]


        graph.add_node(

            f"case:{case_id}",

            node_type="case",

            case_id=case_id

        )


    # --------------------------------------------------------
    # Entity nodes + relationships
    # --------------------------------------------------------

    for fingerprint in fingerprints:

        case_id = fingerprint[
            "case_id"
        ]


        case_node = (
            f"case:{case_id}"
        )


        # Shared wallet entities

        for wallet in fingerprint[
            "wallets"
        ]:

            wallet_node = (
                f"wallet:{wallet}"
            )


            graph.add_node(

                wallet_node,

                node_type="wallet",

                address=wallet

            )


            graph.add_edge(

                case_node,

                wallet_node,

                relationship="contains_wallet"

            )


        # Shared destination entities

        for destination in fingerprint[
            "destinations"
        ]:

            destination_node = (
                f"destination:{destination}"
            )


            graph.add_node(

                destination_node,

                node_type="destination",

                address=destination

            )


            graph.add_edge(

                case_node,

                destination_node,

                relationship="destination"

            )


    # ========================================================
    # FIND CONNECTED COMPONENTS
    # ========================================================

    components = list(
        nx.connected_components(
            graph
        )
    )


    clusters = []


    cluster_number = 1


    for component in components:

        case_ids = []


        wallets = []

        destinations = []


        for node in component:

            data = graph.nodes[
                node
            ]


            node_type = data.get(
                "node_type"
            )


            if node_type == "case":

                case_ids.append(
                    data.get(
                        "case_id"
                    )
                )


            elif node_type == "wallet":

                wallets.append(
                    data.get(
                        "address"
                    )
                )


            elif node_type == "destination":

                destinations.append(
                    data.get(
                        "address"
                    )
                )


        # Only meaningful clusters

        if len(
            case_ids
        ) < 2:

            continue


        clusters.append({

            "cluster_id":
                f"RING-{cluster_number:03d}",

            "case_ids":
                sorted(
                    case_ids
                ),

            "shared_wallets":
                sorted(
                    set(
                        wallets
                    )
                ),

            "shared_destinations":
                sorted(
                    set(
                        destinations
                    )
                ),

            "case_count":
                len(
                    case_ids
                ),

            "investigation_note":
                (
                    "Cases are connected through one or more "
                    "shared blockchain entities. This represents "
                    "a potential investigation cluster, not a "
                    "confirmed fraud ring."
                )

        })


        cluster_number += 1


    return clusters


# ============================================================
# CONVERGENCE SUMMARY
# ============================================================

def convergence_summary(
    convergence_results
):

    if not convergence_results:

        return {

            "linked_cases":
                0,

            "high_connections":
                0,

            "medium_connections":
                0,

            "shared_wallet_count":
                0,

            "shared_destination_count":
                0,

            "status":
                "No cross-case overlap detected"

        }


    shared_wallets = set()

    shared_destinations = set()


    for result in convergence_results:

        for wallet in result.get(
            "shared_wallets",
            []
        ):

            shared_wallets.add(
                wallet
            )


        for destination in result.get(
            "shared_destinations",
            []
        ):

            shared_destinations.add(
                destination
            )


    return {

        "linked_cases":
            len(
                convergence_results
            ),

        "high_connections":
            sum(

                1

                for result
                in convergence_results

                if result.get(
                    "severity"
                ) == "HIGH"

            ),

        "medium_connections":
            sum(

                1

                for result
                in convergence_results

                if result.get(
                    "severity"
                ) == "MEDIUM"

            ),

        "shared_wallet_count":
            len(
                shared_wallets
            ),

        "shared_destination_count":
            len(
                shared_destinations
            ),

        "status":
            "Potential cross-case connections detected"

    }


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def detect_convergence(
    current_case,
    previous_cases
):

    return detect_cross_case_convergence(
        current_case,
        previous_cases
    )


def build_clusters(
    cases
):

    return build_fraud_ring_clusters(
        cases
    )

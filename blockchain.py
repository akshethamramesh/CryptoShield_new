import os
import requests
from collections import Counter, deque
from dotenv import load_dotenv


# ============================================================
# CRYPTOSHIELD - MULTI-CHAIN BLOCKCHAIN ANALYTICS ENGINE
# ============================================================
#
# Workflow:
#
# Reported Wallet
#       ↓
# Blockchain API
#       ↓
# Native + Token Transactions
#       ↓
# Multi-Hop BFS
#       ↓
# Wallet Network
#       ↓
# Fund Flow
#
# IMPORTANT:
# BFS calculates wallet relationship distance.
# Transaction arrows ALWAYS represent:
#
# transaction["from"] → transaction["to"]
#
# ============================================================


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

try:
    import streamlit as st

    if not ETHERSCAN_API_KEY:
        ETHERSCAN_API_KEY = st.secrets.get(
            "ETHERSCAN_API_KEY",
            ""
        )

except Exception:
    pass


# ============================================================
# API CONFIGURATION
# ============================================================

ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"


# Supported EVM chains.
#
# These use Etherscan-compatible V2 chain IDs.
#
CHAIN_IDS = {
    "Ethereum": 1,
    "BSC": 56,
    "Polygon": 137,
    "Base": 8453,
    "Arbitrum": 42161,
    "Optimism": 10
}


# Native asset names for UI/reporting.

CHAIN_NATIVE_ASSETS = {
    "Ethereum": "ETH",
    "BSC": "BNB",
    "Polygon": "POL",
    "Base": "ETH",
    "Arbitrum": "ETH",
    "Optimism": "ETH"
}


# ============================================================
# LIMITS
# ============================================================

MAX_WALLETS_PER_NODE = 5

MAX_TRANSFERS_PER_WALLET = 100

MAX_TOKEN_TRANSFERS_PER_WALLET = 100

MAX_PAGES = 3

REQUEST_TIMEOUT = 20


# ============================================================
# CACHE
# ============================================================

transaction_cache = {}

api_status = {}


# ============================================================
# ADDRESS HELPERS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def is_valid_evm_address(address):

    address = normalize_address(address)

    return (
        address.startswith("0x")
        and len(address) == 42
    )


# ============================================================
# CHAIN HELPERS
# ============================================================

def get_chain_id(chain):

    return CHAIN_IDS.get(
        chain,
        CHAIN_IDS["Ethereum"]
    )


def get_native_asset(chain):

    return CHAIN_NATIVE_ASSETS.get(
        chain,
        "ETH"
    )


def get_supported_chains():

    return list(
        CHAIN_IDS.keys()
    )


# ============================================================
# API REQUEST
# ============================================================

def etherscan_request(params):

    if not ETHERSCAN_API_KEY:

        api_status["error"] = (
            "ETHERSCAN_API_KEY not configured"
        )

        print(
            "ERROR: ETHERSCAN_API_KEY not found."
        )

        return []


    try:

        response = requests.get(
            ETHERSCAN_V2_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()


        status = str(
            data.get("status", "")
        )

        message = data.get(
            "message",
            ""
        )

        result = data.get(
            "result",
            []
        )


        # Store API status for UI/debugging.

        api_status["status"] = status

        api_status["message"] = message


        # Etherscan may return a message
        # even when result is not a list.

        if isinstance(result, list):

            return result


        # API errors can sometimes appear
        # inside result as a string.

        if isinstance(result, str):

            api_status["error"] = result

            print(
                "Blockchain API:",
                result
            )

            return []


        return []


    except requests.exceptions.Timeout:

        api_status["error"] = (
            "Blockchain API request timed out"
        )

        print(
            "Blockchain API timeout."
        )

        return []


    except requests.exceptions.RequestException as error:

        api_status["error"] = str(error)

        print(
            "Blockchain API request error:",
            error
        )

        return []


    except Exception as error:

        api_status["error"] = str(error)

        print(
            "Unexpected blockchain API error:",
            error
        )

        return []


# ============================================================
# GET API STATUS
# ============================================================

def get_api_status():

    return dict(
        api_status
    )


# ============================================================
# NATIVE TRANSACTIONS
# ============================================================

def get_normal_transactions(
    wallet,
    chain="Ethereum"
):

    wallet = normalize_address(
        wallet
    )

    chain_id = get_chain_id(
        chain
    )


    if not wallet:

        return []


    cache_key = (
        f"{chain}:{wallet}:normal"
    )


    if cache_key in transaction_cache:

        return transaction_cache[
            cache_key
        ]


    all_transactions = []


    for page in range(
        1,
        MAX_PAGES + 1
    ):

        params = {

            "chainid":
                chain_id,

            "module":
                "account",

            "action":
                "txlist",

            "address":
                wallet,

            "startblock":
                0,

            "endblock":
                99999999,

            "page":
                page,

            "offset":
                MAX_TRANSFERS_PER_WALLET,

            "sort":
                "desc",

            "apikey":
                ETHERSCAN_API_KEY
        }


        result = etherscan_request(
            params
        )


        if not result:

            break


        for tx in result:

            tx = dict(tx)

            tx["type"] = "native"

            tx["chain"] = chain

            tx["asset"] = get_native_asset(
                chain
            )


            try:

                raw_value = int(
                    tx.get(
                        "value",
                        0
                    )
                )

                tx["value"] = (
                    raw_value / 10**18
                )

            except Exception:

                tx["value"] = 0


            all_transactions.append(
                tx
            )


        if len(result) < MAX_TRANSFERS_PER_WALLET:

            break


    all_transactions = (
        all_transactions[
            :MAX_TRANSFERS_PER_WALLET
        ]
    )


    transaction_cache[
        cache_key
    ] = all_transactions


    return all_transactions


# ============================================================
# TOKEN TRANSACTIONS
# ============================================================

def get_token_transactions(
    wallet,
    chain="Ethereum"
):

    wallet = normalize_address(
        wallet
    )

    chain_id = get_chain_id(
        chain
    )


    if not wallet:

        return []


    cache_key = (
        f"{chain}:{wallet}:token"
    )


    if cache_key in transaction_cache:

        return transaction_cache[
            cache_key
        ]


    all_transactions = []


    for page in range(
        1,
        MAX_PAGES + 1
    ):

        params = {

            "chainid":
                chain_id,

            "module":
                "account",

            "action":
                "tokentx",

            "address":
                wallet,

            "startblock":
                0,

            "endblock":
                99999999,

            "page":
                page,

            "offset":
                MAX_TOKEN_TRANSFERS_PER_WALLET,

            "sort":
                "desc",

            "apikey":
                ETHERSCAN_API_KEY
        }


        result = etherscan_request(
            params
        )


        if not result:

            break


        for tx in result:

            tx = dict(tx)

            tx["type"] = "token"

            tx["chain"] = chain


            token_symbol = tx.get(
                "tokenSymbol",
                "TOKEN"
            )

            tx["asset"] = token_symbol


            try:

                raw_value = int(
                    tx.get(
                        "value",
                        0
                    )
                )

                decimals = int(
                    tx.get(
                        "tokenDecimal",
                        18
                    )
                )

                tx["value"] = (
                    raw_value /
                    (10 ** decimals)
                )

            except Exception:

                tx["value"] = 0


            all_transactions.append(
                tx
            )


        if len(result) < MAX_TOKEN_TRANSFERS_PER_WALLET:

            break


    all_transactions = (
        all_transactions[
            :MAX_TOKEN_TRANSFERS_PER_WALLET
        ]
    )


    transaction_cache[
        cache_key
    ] = all_transactions


    return all_transactions


# ============================================================
# DEDUPLICATE TRANSACTIONS
# ============================================================

def deduplicate_transactions(
    transactions
):

    seen = set()

    unique_transactions = []


    for tx in transactions:

        tx_hash = tx.get(
            "hash",
            ""
        )

        log_index = tx.get(
            "logIndex",
            ""
        )

        tx_type = tx.get(
            "type",
            "native"
        )

        chain = tx.get(
            "chain",
            ""
        )


        identifier = (

            chain,

            tx_hash,

            log_index,

            tx_type
        )


        if identifier in seen:

            continue


        seen.add(
            identifier
        )

        unique_transactions.append(
            tx
        )


    return unique_transactions


# ============================================================
# COMBINED WALLET TRANSACTIONS
# ============================================================

def get_wallet_transactions(
    wallet,
    chain="Ethereum",
    include_tokens=True
):

    wallet = normalize_address(
        wallet
    )


    if not wallet:

        return []


    cache_key = (
        f"{chain}:{wallet}:combined"
    )


    if cache_key in transaction_cache:

        return transaction_cache[
            cache_key
        ]


    transactions = []


    transactions.extend(
        get_normal_transactions(
            wallet,
            chain
        )
    )


    if include_tokens:

        transactions.extend(
            get_token_transactions(
                wallet,
                chain
            )
        )


    transactions = (
        deduplicate_transactions(
            transactions
        )
    )


    transactions.sort(

        key=lambda tx:
            int(
                tx.get(
                    "timeStamp",
                    0
                )
                or 0
            ),

        reverse=True
    )


    transaction_cache[
        cache_key
    ] = transactions


    return transactions


# ============================================================
# BUILD RELATIONSHIP GRAPH
# ============================================================

def build_transaction_graph(
    transactions
):

    graph = {}


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


        if not sender or not receiver:

            continue


        if sender == receiver:

            continue


        if sender not in graph:

            graph[sender] = set()


        if receiver not in graph:

            graph[receiver] = set()


        # Undirected relationship graph
        # is used ONLY for hop discovery.

        graph[sender].add(
            receiver
        )

        graph[receiver].add(
            sender
        )


    return graph


# ============================================================
# BFS HOP CALCULATION
# ============================================================

def calculate_wallet_hops(
    start_wallet,
    transactions,
    max_hop=3
):

    start_wallet = normalize_address(
        start_wallet
    )


    if not start_wallet:

        return {}


    graph = build_transaction_graph(
        transactions
    )


    queue = deque(
        [
            (
                start_wallet,
                0
            )
        ]
    )


    wallet_hops = {

        start_wallet:
            0
    }


    while queue:

        current_wallet, current_hop = (
            queue.popleft()
        )


        if current_hop >= max_hop:

            continue


        for neighbour in graph.get(
            current_wallet,
            set()
        ):

            if neighbour in wallet_hops:

                continue


            next_hop = (
                current_hop + 1
            )


            wallet_hops[
                neighbour
            ] = next_hop


            queue.append(
                (
                    neighbour,
                    next_hop
                )
            )


    return wallet_hops


# ============================================================
# FUND FLOW CONNECTIONS
# ============================================================

def build_fund_flow_connections(
    transactions,
    wallet_hops,
    max_hop=3
):

    connections = []

    seen = set()


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


        if not sender or not receiver:

            continue


        if sender == receiver:

            continue


        if sender not in wallet_hops:

            continue


        if receiver not in wallet_hops:

            continue


        sender_hop = wallet_hops[
            sender
        ]

        receiver_hop = wallet_hops[
            receiver
        ]


        if (
            sender_hop > max_hop
            or receiver_hop > max_hop
        ):

            continue


        tx_hash = tx.get(
            "hash",
            ""
        )

        log_index = tx.get(
            "logIndex",
            ""
        )

        tx_type = tx.get(
            "type",
            "native"
        )

        chain = tx.get(
            "chain",
            ""
        )


        edge_id = (

            sender,

            receiver,

            tx_hash,

            log_index,

            tx_type,

            chain
        )


        if edge_id in seen:

            continue


        seen.add(
            edge_id
        )


        connections.append(
            {

                "from":
                    sender,

                "to":
                    receiver,

                "hop":
                    max(
                        sender_hop,
                        receiver_hop
                    ),

                "from_hop":
                    sender_hop,

                "to_hop":
                    receiver_hop,

                "tx_hash":
                    tx_hash,

                "log_index":
                    log_index,

                "type":
                    tx_type,

                "chain":
                    chain,

                "asset":
                    tx.get(
                        "asset",
                        ""
                    ),

                "value":
                    tx.get(
                        "value",
                        0
                    ),

                "timestamp":
                    tx.get(
                        "timeStamp",
                        0
                    )
            }
        )


    return connections


# ============================================================
# FIND CONNECTED WALLETS
# ============================================================

def find_connected_wallets(
    transactions,
    current_wallet
):

    current_wallet = normalize_address(
        current_wallet
    )


    wallet_counter = Counter()


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


        if sender and sender != current_wallet:

            wallet_counter[
                sender
            ] += 1


        if receiver and receiver != current_wallet:

            wallet_counter[
                receiver
            ] += 1


    return [

        wallet

        for wallet, count

        in wallet_counter.most_common(
            MAX_WALLETS_PER_NODE
        )

    ]


# ============================================================
# MULTI-HOP WALLET TRACE
# ============================================================

def trace_wallet(
    start_wallet,
    chain="Ethereum",
    max_hop=3
):

    start_wallet = normalize_address(
        start_wallet
    )


    if not start_wallet:

        return {

            "start_wallet":
                "",

            "chain":
                chain,

            "transactions":
                [],

            "visited_wallets":
                [],

            "connected_wallets":
                [],

            "wallet_hops":
                {},

            "connections":
                [],

            "max_hop":
                max_hop,

            "api_status":
                get_api_status()

        }


    queue = deque(
        [
            (
                start_wallet,
                0
            )
        ]
    )


    processed = set()


    wallet_hops = {

        start_wallet:
            0
    }


    all_transactions = []


    while queue:

        current_wallet, current_hop = (
            queue.popleft()
        )


        current_wallet = normalize_address(
            current_wallet
        )


        if current_wallet in processed:

            continue


        processed.add(
            current_wallet
        )


        transactions = get_wallet_transactions(

            current_wallet,

            chain=chain,

            include_tokens=True
        )


        for tx in transactions:

            tx_copy = tx.copy()

            tx_copy[
                "traced_wallet"
            ] = current_wallet

            tx_copy[
                "hop"
            ] = current_hop

            all_transactions.append(
                tx_copy
            )


        if current_hop >= max_hop:

            continue


        connected_wallets = (
            find_connected_wallets(
                transactions,
                current_wallet
            )
        )


        for wallet in connected_wallets:

            wallet = normalize_address(
                wallet
            )


            if not wallet:

                continue


            if wallet == current_wallet:

                continue


            next_hop = (
                current_hop + 1
            )


            if next_hop > max_hop:

                continue


            if wallet not in wallet_hops:

                wallet_hops[
                    wallet
                ] = next_hop


                queue.append(
                    (
                        wallet,
                        next_hop
                    )
                )


    # --------------------------------------------------------
    # Remove duplicate transactions
    # --------------------------------------------------------

    all_transactions = (
        deduplicate_transactions(
            all_transactions
        )
    )


    all_transactions.sort(

        key=lambda tx:
            int(
                tx.get(
                    "timeStamp",
                    0
                )
                or 0
            ),

        reverse=True
    )


    # --------------------------------------------------------
    # Recalculate shortest relationship hops
    # --------------------------------------------------------

    final_wallet_hops = (
        calculate_wallet_hops(

            start_wallet,

            all_transactions,

            max_hop=max_hop
        )
    )


    final_wallet_hops[
        start_wallet
    ] = 0


    # --------------------------------------------------------
    # Build actual fund-flow edges
    # --------------------------------------------------------

    connections = (
        build_fund_flow_connections(

            all_transactions,

            final_wallet_hops,

            max_hop=max_hop
        )
    )


    visited_wallets = list(
        final_wallet_hops.keys()
    )


    visited_wallets.sort(

        key=lambda wallet: (

            final_wallet_hops.get(
                wallet,
                999
            ),

            wallet
        )
    )


    connected_wallets = [

        wallet

        for wallet in visited_wallets

        if wallet != start_wallet

    ]


    return {

        "start_wallet":
            start_wallet,

        "chain":
            chain,

        "native_asset":
            get_native_asset(
                chain
            ),

        "transactions":
            all_transactions,

        "visited_wallets":
            visited_wallets,

        "connected_wallets":
            connected_wallets,

        "wallet_hops":
            final_wallet_hops,

        "connections":
            connections,

        "max_hop":
            max_hop,

        "api_status":
            get_api_status()

    }


# ============================================================
# COMPATIBILITY FUNCTIONS
# ============================================================

def recursive_trace(
    wallet,
    chain="Ethereum",
    max_hop=3
):

    return trace_wallet(

        start_wallet=wallet,

        chain=chain,

        max_hop=max_hop

    )


def clear_transaction_cache():

    transaction_cache.clear()


def clear_cache():

    clear_transaction_cache()


def get_cache_size():

    return len(
        transaction_cache
    )


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )

    print(
        "       CRYPTOSHIELD BLOCKCHAIN TEST"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "Supported chains:"
    )

    for chain in get_supported_chains():

        print(
            f" - {chain}"
        )

    print()

    wallet = input(
        "Enter EVM wallet address: "
    ).strip()


    if not wallet:

        raise SystemExit


    if not is_valid_evm_address(wallet):

        print(
            "Invalid EVM wallet address."
        )

        raise SystemExit


    chain = input(
        "Enter chain "
        "(Ethereum/BSC/Polygon/Base/Arbitrum/Optimism): "
    ).strip()


    if chain not in CHAIN_IDS:

        print(
            "Unsupported chain."
        )

        raise SystemExit


    result = trace_wallet(

        wallet,

        chain=chain,

        max_hop=3

    )


    print()

    print(
        "Transactions found:",
        len(
            result[
                "transactions"
            ]
        )
    )

    print(
        "Wallets discovered:",
        len(
            result[
                "visited_wallets"
            ]
        )
    )

    print(
        "Fund-flow connections:",
        len(
            result[
                "connections"
            ]
        )
    )

    print(
        "Maximum hop:",
        result[
            "max_hop"
        ]
    )

    print()

    print(
        "API status:",
        result.get(
            "api_status",
            {}
        )
    )

import os
import tempfile
from collections import deque

import networkx as nx


# ============================================================
# CRYPTOSHIELD - FUND FLOW GRAPH
# ============================================================
#
# Wallet       -> Node
# Transaction  -> Edge
# Hop          -> Distance from reported wallet
#
# The graph is an investigation visualization.
# It does NOT prove ownership or criminal activity.
#
# ============================================================


MAX_GRAPH_NODES = 60
MAX_GRAPH_EDGES = 120


# ============================================================
# HELPERS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def safe_float(value):

    try:
        return float(value)

    except Exception:
        return 0.0


def short_address(address):

    address = str(address)

    if len(address) <= 14:

        return address

    return (
        address[:7]
        + "..."
        + address[-5:]
    )


# ============================================================
# BUILD TRANSACTION GRAPH
# ============================================================

def build_transaction_graph(
    transactions,
    start_wallet=None
):

    graph = nx.DiGraph()


    start_wallet = normalize_address(
        start_wallet
    )


    # --------------------------------------------------------
    # Add transaction edges
    # --------------------------------------------------------

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


        value = safe_float(
            tx.get(
                "value",
                0
            )
        )


        tx_hash = tx.get(
            "hash",
            ""
        )


        timestamp = tx.get(
            "timeStamp",
            ""
        )


        # ----------------------------------------------------
        # Add nodes
        # ----------------------------------------------------

        graph.add_node(
            sender
        )

        graph.add_node(
            receiver
        )


        # ----------------------------------------------------
        # Multiple transactions between same wallets
        # are aggregated into one visual edge.
        # ----------------------------------------------------

        if graph.has_edge(
            sender,
            receiver
        ):

            edge = graph[
                sender
            ][
                receiver
            ]


            edge[
                "transaction_count"
            ] += 1


            edge[
                "total_value"
            ] += value


            if tx_hash:

                edge[
                    "hashes"
                ].append(
                    tx_hash
                )


        else:

            graph.add_edge(

                sender,

                receiver,

                transaction_count=1,

                total_value=value,

                hashes=(
                    [tx_hash]
                    if tx_hash
                    else []
                ),

                timestamp=timestamp

            )


    # --------------------------------------------------------
    # Ensure reported wallet exists
    # --------------------------------------------------------

    if start_wallet:

        graph.add_node(
            start_wallet
        )


    return graph


# ============================================================
# CALCULATE HOPS
# ============================================================

def calculate_hops(
    graph,
    start_wallet,
    max_hop=3
):

    start_wallet = normalize_address(
        start_wallet
    )


    if not start_wallet:

        return {}


    if start_wallet not in graph:

        return {
            start_wallet: 0
        }


    # --------------------------------------------------------
    # Treat fund-flow network as connected for discovery.
    # Direction is still preserved in the actual graph.
    # --------------------------------------------------------

    undirected = graph.to_undirected()


    distances = nx.single_source_shortest_path_length(

        undirected,

        start_wallet,

        cutoff=max_hop

    )


    return dict(
        distances
    )


# ============================================================
# ADD HOP DATA
# ============================================================

def annotate_graph_with_hops(
    graph,
    start_wallet,
    max_hop=3
):

    hops = calculate_hops(
        graph,
        start_wallet,
        max_hop
    )


    for node in graph.nodes:

        graph.nodes[
            node
        ][
            "hop"
        ] = hops.get(
            node
        )


    for sender, receiver in graph.edges:

        sender_hop = graph.nodes[
            sender
        ].get(
            "hop"
        )


        receiver_hop = graph.nodes[
            receiver
        ].get(
            "hop"
        )


        graph.edges[
            sender,
            receiver
        ][
            "progression"
        ] = (

            sender_hop is not None
            and receiver_hop is not None
            and receiver_hop > sender_hop

        )


    return graph


# ============================================================
# LIMIT GRAPH SIZE
# ============================================================

def limit_graph(
    graph,
    start_wallet,
    max_nodes=MAX_GRAPH_NODES,
    max_edges=MAX_GRAPH_EDGES
):

    start_wallet = normalize_address(
        start_wallet
    )


    if (
        graph.number_of_nodes()
        <= max_nodes
        and
        graph.number_of_edges()
        <= max_edges
    ):

        return graph


    # --------------------------------------------------------
    # Keep reported wallet always
    # --------------------------------------------------------

    selected_nodes = set()


    if start_wallet in graph:

        selected_nodes.add(
            start_wallet
        )


    # --------------------------------------------------------
    # Prefer low-hop nodes
    # --------------------------------------------------------

    sorted_nodes = sorted(

        graph.nodes,

        key=lambda node: (

            graph.nodes[
                node
            ].get(
                "hop"
            )
            if graph.nodes[
                node
            ].get(
                "hop"
            ) is not None
            else 999

        )

    )


    for node in sorted_nodes:

        if len(
            selected_nodes
        ) >= max_nodes:

            break


        selected_nodes.add(
            node
        )


    limited = graph.subgraph(
        selected_nodes
    ).copy()


    # --------------------------------------------------------
    # Limit edges by transaction value
    # --------------------------------------------------------

    if (
        limited.number_of_edges()
        > max_edges
    ):

        ranked_edges = sorted(

            limited.edges(
                data=True
            ),

            key=lambda item:
                item[2].get(
                    "total_value",
                    0
                ),

            reverse=True

        )


        keep_edges = ranked_edges[
            :max_edges
        ]


        final_graph = nx.DiGraph()


        for node in limited.nodes:

            final_graph.add_node(

                node,

                **limited.nodes[
                    node
                ]

            )


        for sender, receiver, data in keep_edges:

            final_graph.add_edge(

                sender,

                receiver,

                **data

            )


        return final_graph


    return limited


# ============================================================
# GRAPH STATISTICS
# ============================================================

def graph_statistics(
    graph,
    start_wallet=None
):

    start_wallet = normalize_address(
        start_wallet
    )


    hop_counts = {}


    for node in graph.nodes:

        hop = graph.nodes[
            node
        ].get(
            "hop"
        )


        if hop is None:

            continue


        hop_counts[
            hop
        ] = (
            hop_counts.get(
                hop,
                0
            )
            + 1
        )


    return {

        "nodes":
            graph.number_of_nodes(),

        "edges":
            graph.number_of_edges(),

        "reported_wallet":
            start_wallet,

        "hop_counts":
            hop_counts,

        "max_observed_hop":
            max(
                hop_counts.keys()
            )
            if hop_counts
            else 0

    }


# ============================================================
# GENERATE PYVIS HTML
# ============================================================

def generate_pyvis_graph(
    graph,
    start_wallet,
    output_file="cryptoshield_graph.html"
):

    try:

        from pyvis.network import Network

    except ImportError:

        return None


    net = Network(

        height="650px",

        width="100%",

        directed=True,

        bgcolor="#ffffff",

        font_color="#111111"

    )


    # --------------------------------------------------------
    # Physics
    # --------------------------------------------------------

    net.barnes_hut(

        gravity=-3500,

        central_gravity=0.2,

        spring_length=180,

        spring_strength=0.03,

        damping=0.9

    )


    start_wallet = normalize_address(
        start_wallet
    )


    # --------------------------------------------------------
    # Add nodes
    # --------------------------------------------------------

    for node in graph.nodes:

        hop = graph.nodes[
            node
        ].get(
            "hop"
        )


        if node == start_wallet:

            label = (
                "REPORTED WALLET\n"
                + short_address(node)
            )

            title = (
                f"Reported Wallet<br>"
                f"Address: {node}<br>"
                f"Hop: 0"
            )


        else:

            hop_text = (
                str(hop)
                if hop is not None
                else "Unknown"
            )


            label = (
                f"Hop {hop_text}\n"
                f"{short_address(node)}"
            )


            title = (
                f"Wallet: {node}<br>"
                f"Hop: {hop_text}"
            )


        # ----------------------------------------------------
        # Size by degree
        # ----------------------------------------------------

        degree = graph.degree(
            node
        )


        size = min(
            18 + degree * 4,
            45
        )


        net.add_node(

            node,

            label=label,

            title=title,

            size=size

        )


    # --------------------------------------------------------
    # Add edges
    # --------------------------------------------------------

    for sender, receiver, data in graph.edges(
        data=True
    ):

        value = data.get(
            "total_value",
            0
        )


        count = data.get(
            "transaction_count",
            1
        )


        progression = data.get(
            "progression",
            False
        )


        title = (

            f"From: {sender}<br>"

            f"To: {receiver}<br>"

            f"Transactions: {count}<br>"

            f"Total value: {value:.6f}"

        )


        # ----------------------------------------------------
        # Width based on transaction count
        # ----------------------------------------------------

        width = min(
            1 + count * 1.5,
            8
        )


        net.add_edge(

            sender,

            receiver,

            title=title,

            width=width,

            arrows="to"

        )


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:

        net.write_html(
            output_file,
            open_browser=False
        )

        return output_file

    except Exception:

        return None


# ============================================================
# RENDER IN STREAMLIT
# ============================================================

def render_fund_flow_graph(
    transactions,
    start_wallet,
    max_hop=3
):

    try:

        import streamlit as st

    except ImportError:

        return None


    # --------------------------------------------------------
    # Build graph
    # --------------------------------------------------------

    graph = build_transaction_graph(

        transactions,

        start_wallet

    )


    if graph.number_of_nodes() == 0:

        st.info(
            "No transaction relationships available for graph visualization."
        )

        return None


    # --------------------------------------------------------
    # Hop calculation
    # --------------------------------------------------------

    graph = annotate_graph_with_hops(

        graph,

        start_wallet,

        max_hop

    )


    # --------------------------------------------------------
    # Remove nodes outside selected hop range
    # --------------------------------------------------------

    allowed_nodes = [

        node

        for node in graph.nodes

        if (

            graph.nodes[
                node
            ].get(
                "hop"
            ) is not None

            and

            graph.nodes[
                node
            ].get(
                "hop"
            ) <= max_hop

        )

        or normalize_address(
            node
        )
        ==
        normalize_address(
            start_wallet
        )

    ]


    graph = graph.subgraph(
        allowed_nodes
    ).copy()


    # --------------------------------------------------------
    # Limit graph size
    # --------------------------------------------------------

    graph = limit_graph(

        graph,

        start_wallet

    )


    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    stats = graph_statistics(

        graph,

        start_wallet

    )


    col1, col2, col3, col4 = st.columns(4)


    col1.metric(
        "Wallets",
        stats[
            "nodes"
        ]
    )


    col2.metric(
        "Connections",
        stats[
            "edges"
        ]
    )


    col3.metric(
        "Max Hop",
        stats[
            "max_observed_hop"
        ]
    )


    col4.metric(

        "Reported Wallet",

        short_address(
            start_wallet
        )

    )


    # --------------------------------------------------------
    # Generate HTML
    # --------------------------------------------------------

    output_file = os.path.join(

        tempfile.gettempdir(),

        "cryptoshield_fund_flow.html"

    )


    result = generate_pyvis_graph(

        graph,

        start_wallet,

        output_file

    )


    if result is None:

        st.warning(

            "PyVis is not installed. "
            "Install it using: pip install pyvis"

        )

        return None


    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    try:

        from streamlit.components.v1 import html


        with open(

            result,

            "r",

            encoding="utf-8"

        ) as file:

            html_content = file.read()


        html(

            html_content,

            height=700,

            scrolling=True

        )


    except Exception as error:

        st.error(
            f"Unable to render graph: {error}"
        )


    # --------------------------------------------------------
    # Legend
    # --------------------------------------------------------

    st.markdown(
        """
        **Graph interpretation**

        - **Reported Wallet** → starting investigation address
        - **Hop 1** → directly connected wallet
        - **Hop 2** → next-level connected wallet
        - **Hop 3+** → deeper traced participants
        - **Arrow** → transaction direction

        *Graph relationships are analytical evidence and do not
        independently establish ownership or criminal activity.*
        """
    )


    return graph


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

def build_fund_flow_graph(
    transactions,
    start_wallet,
    max_hop=3
):

    graph = build_transaction_graph(

        transactions,

        start_wallet

    )


    return annotate_graph_with_hops(

        graph,

        start_wallet,

        max_hop

    )

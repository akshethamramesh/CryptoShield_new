import os
import json
import hashlib
from datetime import datetime

import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CryptoShield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# SAFE IMPORTS
# ============================================================

# Blockchain
try:
    from blockchain import trace_wallet
except Exception:
    trace_wallet = None


# VASP detection
try:
    from vasp_detection import (
        detect_known_vasps,
        find_vasp_for_wallet,
        load_exchange_labels
    )

except ImportError:

    # Compatibility with old vasp_detection.py
    try:
        from vasp_detection import detect_vasp

        detect_known_vasps = None
        find_vasp_for_wallet = None
        load_exchange_labels = None

    except ImportError:

        detect_known_vasps = None
        find_vasp_for_wallet = None
        load_exchange_labels = None


# Demo data
try:
    from demo_data import get_demo_transactions
except Exception:
    get_demo_transactions = None


# Fund-flow graph
try:
    from fund_flow_graph import render_fund_flow_graph
except Exception:
    render_fund_flow_graph = None


# KYC / RPA
try:
    from kyc_rpa import (
        build_case_evidence,
        evidence_hash,
        prepare_request,
        mark_human_review,
        authorize_submission,
        simulate_vasp_response
    )
except Exception:
    build_case_evidence = None
    evidence_hash = None
    prepare_request = None
    mark_human_review = None
    authorize_submission = None
    simulate_vasp_response = None


# PDF reports
try:
    from report_generator import (
        generate_investigation_pdf,
        generate_rpa_request_pdf
    )
except Exception:
    generate_investigation_pdf = None
    generate_rpa_request_pdf = None


# ============================================================
# CONSTANTS
# ============================================================

APP_VERSION = "CryptoShield SIH Prototype v2.0"


# ============================================================
# VASP REGISTRY FALLBACK
# ============================================================
#
# This is used even if exchange_labels.json is missing.
# The addresses are public attribution examples.
#
# IMPORTANT:
# A public address attribution does NOT prove that a specific
# person owns or controls the wallet.
# ============================================================

FALLBACK_VASP_REGISTRY = {

    "0x1111111111111111111111111111111111111111": {
        "name": "Demo Exchange Alpha",
        "type": "Centralized Exchange",
        "country": "Demo",
        "label_source": "CryptoShield Demo Registry"
    },

    "0x2222222222222222222222222222222222222222": {
        "name": "Demo Exchange Beta",
        "type": "Centralized Exchange",
        "country": "Demo",
        "label_source": "CryptoShield Demo Registry"
    },

    "0x3333333333333333333333333333333333333333": {
        "name": "Demo Exchange Gamma",
        "type": "Centralized Exchange",
        "country": "Demo",
        "label_source": "CryptoShield Demo Registry"
    },

    "0x28c6c06298d514db089934071355e5743bf21d60": {
        "name": "Binance 14",
        "type": "Centralized Exchange / VASP",
        "country": "Global",
        "label_source": "Public blockchain address attribution"
    },

    "0x503828976d22510aad0201ac7ec88293211d23da": {
        "name": "Coinbase 2",
        "type": "Centralized Exchange / VASP",
        "country": "United States",
        "label_source": "Public blockchain address attribution"
    }
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def load_registry():

    registry = {}

    # Try exchange_labels.json first
    try:

        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "exchange_labels.json"
        )

        if os.path.exists(path):

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

                if isinstance(data, dict):

                    for address, info in data.items():

                        if isinstance(info, dict):

                            registry[
                                normalize_address(address)
                            ] = info

    except Exception:
        pass

    # Add fallback values
    for address, info in FALLBACK_VASP_REGISTRY.items():

        if address not in registry:

            registry[address] = info

    return registry


def extract_tx_addresses(tx):

    addresses = []

    if not isinstance(tx, dict):
        return addresses

    fields = [
        "from",
        "to",
        "from_address",
        "to_address",
        "sender",
        "receiver",
        "wallet",
        "address"
    ]

    for field in fields:

        value = tx.get(field)

        if isinstance(value, str):

            if value.strip():

                addresses.append(
                    normalize_address(value)
                )

    return addresses


# ============================================================
# VASP DETECTION ENGINE
# ============================================================

def local_vasp_detection(
    transactions,
    reported_wallet
):

    registry = load_registry()

    results = {}

    reported = normalize_address(
        reported_wallet
    )

    # --------------------------------------------------------
    # CHECK INPUT WALLET DIRECTLY
    # --------------------------------------------------------

    if reported in registry:

        info = registry[reported]

        results[reported] = {

            "address": reported,

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

            "role": "Reported wallet",

            "hop": 0,

            "confidence": "High",

            "evidence":
                "The reported wallet directly matches "
                "a curated VASP/exchange address.",

            "kyc_note":
                "Identity information must be requested "
                "from the VASP through applicable "
                "authority and legal process."
        }

    # --------------------------------------------------------
    # CHECK TRANSACTION PARTICIPANTS
    # --------------------------------------------------------

    for tx in transactions or []:

        addresses = extract_tx_addresses(tx)

        hop = (
            tx.get("hop")
            or tx.get("wallet_hop")
            or tx.get("depth")
            or tx.get("trace_depth")
        )

        tx_hash = (
            tx.get("hash")
            or tx.get("tx_hash")
            or tx.get("transaction_hash")
            or ""
        )

        for address in addresses:

            if address not in registry:
                continue

            # Already detected
            if address in results:
                continue

            info = registry[address]

            results[address] = {

                "address": address,

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

                "evidence":
                    "A transaction participant matches "
                    "a curated VASP/exchange address.",

                "transaction_hash": tx_hash,

                "kyc_note":
                    "Identity information must be requested "
                    "from the VASP through applicable "
                    "authority and legal process."
            }

    return list(results.values())


def detect_vasps(
    transactions,
    reported_wallet
):

    """
    Main VASP detection wrapper.

    It first tries the new detector.
    Then falls back to the old detector.
    Finally uses the local registry detector.

    This prevents ImportError/signature problems.
    """

    # --------------------------------------------------------
    # NEW DETECTOR
    # --------------------------------------------------------

    if detect_known_vasps is not None:

        try:

            result = detect_known_vasps(
                transactions=transactions,
                start_wallet=reported_wallet
            )

            if isinstance(result, list):

                # Direct local detection as backup
                local = local_vasp_detection(
                    transactions,
                    reported_wallet
                )

                return merge_vasp_results(
                    result,
                    local
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # OLD DETECTOR
    # --------------------------------------------------------

    try:

        from vasp_detection import detect_vasp

        # Try keyword style
        try:

            result = detect_vasp(
                transactions=transactions,
                start_wallet=reported_wallet
            )

        except Exception:

            # Try old positional style
            try:

                result = detect_vasp(
                    transactions,
                    reported_wallet
                )

            except Exception:

                result = detect_vasp(
                    transactions
                )

        if isinstance(result, list):

            local = local_vasp_detection(
                transactions,
                reported_wallet
            )

            return merge_vasp_results(
                result,
                local
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # LOCAL REGISTRY
    # --------------------------------------------------------

    return local_vasp_detection(
        transactions,
        reported_wallet
    )


def merge_vasp_results(
    primary,
    secondary
):

    merged = {}

    for item in primary or []:

        if not isinstance(item, dict):
            continue

        address = normalize_address(
            item.get("address")
        )

        if address:

            merged[address] = item

    for item in secondary or []:

        if not isinstance(item, dict):
            continue

        address = normalize_address(
            item.get("address")
        )

        if address and address not in merged:

            merged[address] = item

    return list(merged.values())


# ============================================================
# RISK SCORE
# ============================================================

def calculate_risk(
    transactions,
    vasps
):

    transaction_count = len(
        transactions or []
    )

    vasp_count = len(
        vasps or []
    )

    score = 0

    # VASP endpoint identified
    if vasp_count > 0:
        score += 40

    # Transaction activity
    if transaction_count >= 10:
        score += 10

    if transaction_count >= 100:
        score += 10

    if transaction_count >= 1000:
        score += 10

    # Multiple VASP endpoints
    if vasp_count >= 2:
        score += 10

    # Large activity
    if transaction_count >= 5000:
        score += 10

    score = min(
        score,
        100
    )

    if score >= 70:
        level = "HIGH"

    elif score >= 40:
        level = "MEDIUM"

    else:
        level = "LOW"

    return score, level


# ============================================================
# CASE ID
# ============================================================

def create_case_id():

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    return f"CS-{timestamp}"


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 700;
    }

    .subtitle {
        color: #9ca3af;
        font-size: 16px;
    }

    .vasp-card {
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🔎 Investigation")

    st.subheader("Data mode")

    data_mode = st.radio(
        "",
        [
            "Demo / SIH Mode",
            "Live Blockchain Mode"
        ]
    )

    st.subheader(
        "Reported suspect wallet"
    )

    reported_wallet = st.text_input(
        "",
        value="0x28C6c06298d514Db089934071355E5743bf21d60",
        help="Enter an Ethereum-compatible wallet address."
    )

    blockchain = st.selectbox(
        "Blockchain",
        [
            "Ethereum",
            "Base",
            "Polygon",
            "Arbitrum",
            "Optimism",
            "BNB Chain"
        ]
    )

    max_depth = st.slider(
        "Maximum trace depth",
        min_value=1,
        max_value=6,
        value=3
    )

    analyze = st.button(
        "🔎 Analyze Wallet",
        type="primary",
        use_container_width=True
    )

    st.divider()

    st.caption(
        "Wallet analysis produces investigative leads. "
        "It does not directly identify a person from a "
        "blockchain address."
    )


# ============================================================
# INITIAL STATE
# ============================================================

if "case" not in st.session_state:

    st.session_state.case = None


# ============================================================
# ANALYZE WALLET
# ============================================================

if analyze:

    reported_wallet = reported_wallet.strip()

    if not reported_wallet:

        st.error(
            "Please enter a wallet address."
        )

        st.stop()

    with st.spinner(
        "Tracing blockchain transactions..."
    ):

        transactions = []

        api_status = "Demo"

        # ----------------------------------------------------
        # DEMO MODE
        # ----------------------------------------------------

        if data_mode == "Demo / SIH Mode":

            if get_demo_transactions is not None:

                try:

                    transactions = (
                        get_demo_transactions()
                    )

                except Exception:

                    transactions = []

            api_status = "Demo data"

        # ----------------------------------------------------
        # LIVE MODE
        # ----------------------------------------------------

        else:

            if trace_wallet is None:

                st.error(
                    "blockchain.py could not be imported."
                )

                st.stop()

            try:

                result = trace_wallet(
                    reported_wallet,
                    chain=blockchain.lower(),
                    max_hop=max_depth
                )

                if isinstance(result, dict):

                    transactions = result.get(
                        "transactions",
                        []
                    )

                    api_status = result.get(
                        "api_status",
                        "Live blockchain"
                    )

                elif isinstance(result, list):

                    transactions = result

            except TypeError:

                # Compatibility with older trace_wallet()
                try:

                    result = trace_wallet(
                        reported_wallet
                    )

                    if isinstance(result, dict):

                        transactions = result.get(
                            "transactions",
                            []
                        )

                    elif isinstance(result, list):

                        transactions = result

                except Exception as e:

                    st.error(
                        f"Blockchain tracing failed: {e}"
                    )

                    st.stop()

            except Exception as e:

                st.error(
                    f"Blockchain tracing failed: {e}"
                )

                st.stop()

    # --------------------------------------------------------
    # VASP DETECTION
    # --------------------------------------------------------

    with st.spinner(
        "Identifying known VASP endpoints..."
    ):

        vasps = detect_vasps(
            transactions,
            reported_wallet
        )

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk_score, risk_level = calculate_risk(
        transactions,
        vasps
    )

    # --------------------------------------------------------
    # CONNECTED WALLETS
    # --------------------------------------------------------

    connected = set()

    for tx in transactions:

        for address in extract_tx_addresses(tx):

            connected.add(address)

    connected_wallets = len(
        connected
    )

    # --------------------------------------------------------
    # CASE
    # --------------------------------------------------------

    case = {

        "case_id": create_case_id(),

        "start_wallet": reported_wallet,

        "reported_wallet": reported_wallet,

        "chain": blockchain,

        "transactions": transactions,

        "vasp": vasps,

        "risk_score": risk_score,

        "risk_level": risk_level,

        "connected_wallets": connected_wallets,

        "max_hop": max_depth,

        "api_status": api_status,

        "created_at":
            datetime.now().isoformat()
    }

    st.session_state.case = case


# ============================================================
# REQUIRE CASE
# ============================================================

case = st.session_state.case

if case is None:

    st.markdown(
        '<div class="main-title">🛡️ CryptoShield</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Real-Time Crypto Fraud Attribution & '
        'Investigator Workflow'
        '</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Enter a reported wallet and click "
        "**Analyze Wallet** to begin."
    )

    st.stop()


# ============================================================
# CASE DATA
# ============================================================

transactions = case.get(
    "transactions",
    []
)

vasps = case.get(
    "vasp",
    []
)

risk_score = case.get(
    "risk_score",
    0
)

risk_level = case.get(
    "risk_level",
    "LOW"
)


# ============================================================
# TOP HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🛡️ CryptoShield</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Real-Time Crypto Fraud Attribution & '
    'Investigator Workflow'
    '</div>',
    unsafe_allow_html=True
)

st.write("")


# ============================================================
# METRICS
# ============================================================

m1, m2, m3, m4, m5 = st.columns(5)

with m1:

    st.metric(
        "Transactions",
        len(transactions)
    )

with m2:

    st.metric(
        "Connected wallets",
        case.get(
            "connected_wallets",
            0
        )
    )

with m3:

    st.metric(
        "Trace depth",
        case.get(
            "max_hop",
            0
        )
    )

with m4:

    st.metric(
        "Risk",
        f"{risk_score}/100"
    )

with m5:

    st.metric(
        "Level",
        risk_level
    )


# ============================================================
# CASE INFO
# ============================================================

st.write("")

st.markdown(
    f"### Case `{case.get('case_id')}`"
)

st.write(
    f"**Reported wallet:** "
    f"`{case.get('reported_wallet')}` "
    f"• **Blockchain:** "
    f"{case.get('chain')}"
)


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "📊 Overview",
        "🌐 Fund Flow",
        "🚨 Suspicious",
        "🧬 Transaction DNA",
        "🏦 Known VASP",
        "🪪 KYC / Identity",
        "🤖 RPA Workflow",
        "📄 PDF Report"
    ]
)


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tabs[0]:

    st.header(
        "Investigation Overview"
    )

    if vasps:

        st.success(
            f"✅ {len(vasps)} known VASP endpoint(s) identified."
        )

        primary = vasps[0]

        st.subheader(
            "Primary VASP Endpoint"
        )

        c1, c2 = st.columns(2)

        with c1:

            st.write(
                "**Exchange / VASP**"
            )

            st.success(
                primary.get(
                    "name",
                    "Unknown"
                )
            )

            st.write(
                "**Address**"
            )

            st.code(
                primary.get(
                    "address",
                    ""
                )
            )

        with c2:

            st.write(
                "**Type:** "
                + str(
                    primary.get(
                        "type",
                        "Unknown"
                    )
                )
            )

            st.write(
                "**Country:** "
                + str(
                    primary.get(
                        "country",
                        "Unknown"
                    )
                )
            )

            st.write(
                "**Confidence:** "
                + str(
                    primary.get(
                        "confidence",
                        "Unknown"
                    )
                )
            )

    else:

        st.warning(
            "No known VASP endpoint was identified."
        )

        st.write(
            "CryptoShield does not guess an exchange "
            "name. A VASP is shown only when an address "
            "matches the current attribution registry."
        )

    st.divider()

    st.subheader(
        "Investigation Logic"
    )

    st.markdown(
        """
        **Reported wallet**
        ↓

        **Blockchain transaction tracing**
        ↓

        **Address attribution**
        ↓

        **Known VASP / Exchange endpoint**
        ↓

        **Authorized KYC request**
        ↓

        **Human investigator review**
        ↓

        **Authorized submission**
        """
    )


# ============================================================
# TAB 2 — FUND FLOW
# ============================================================

with tabs[1]:

    st.header(
        "Fund Flow"
    )

    if not transactions:

        st.info(
            "No transactions available."
        )

    elif render_fund_flow_graph is not None:

        try:

            render_fund_flow_graph(
                transactions,
                case.get(
                    "reported_wallet"
                ),
                max_hop=case.get(
                    "max_hop",
                    3
                )
            )

        except Exception as e:

            st.warning(
                f"Fund-flow visualization unavailable: {e}"
            )

    else:

        st.info(
            "Fund-flow visualization module is unavailable."
        )


# ============================================================
# TAB 3 — SUSPICIOUS
# ============================================================

with tabs[2]:

    st.header(
        "🚨 Suspicious Activity"
    )

    if not transactions:

        st.info(
            "No transaction data available."
        )

    else:

        st.write(
            f"Analyzed **{len(transactions)}** "
            "transactions."
        )

        if risk_score >= 70:

            st.error(
                f"High-risk investigation lead: "
                f"{risk_score}/100"
            )

        elif risk_score >= 40:

            st.warning(
                f"Moderate investigation lead: "
                f"{risk_score}/100"
            )

        else:

            st.success(
                f"Low current risk signal: "
                f"{risk_score}/100"
            )

        st.write(
            "Risk is an analytical lead and should be "
            "reviewed together with transaction evidence."
        )


# ============================================================
# TAB 4 — TRANSACTION DNA
# ============================================================

with tabs[3]:

    st.header(
        "🧬 Transaction DNA"
    )

    if not transactions:

        st.info(
            "No transactions available."
        )

    else:

        values = []

        for tx in transactions:

            value = (
                tx.get("value")
                or tx.get("amount")
                or 0
            )

            try:
                values.append(
                    float(value)
                )
            except Exception:
                pass

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Transaction count",
                len(transactions)
            )

        with c2:

            st.metric(
                "Unique connected wallets",
                case.get(
                    "connected_wallets",
                    0
                )
            )

        with c3:

            if values:

                st.metric(
                    "Observed volume",
                    f"{sum(values):,.4f}"
                )

            else:

                st.metric(
                    "Observed volume",
                    "N/A"
                )

        st.caption(
            "Transaction DNA summarizes observable "
            "blockchain behavior; it does not identify "
            "a real-world person."
        )


# ============================================================
# TAB 5 — KNOWN VASP
# ============================================================

with tabs[4]:

    st.header(
        "🏦 Known VASP / Exchange Endpoint"
    )

    # --------------------------------------------------------
    # THIS IS THE MAIN FEATURE
    # --------------------------------------------------------

    if not vasps:

        st.warning(
            "No known VASP endpoint was found."
        )

        st.info(
            """
            CryptoShield only displays a VASP when the
            wallet address matches a known public
            attribution in the current registry.

            It does not guess an exchange name.
            """
        )

    else:

        st.success(
            f"✅ {len(vasps)} VASP endpoint(s) identified."
        )

        for index, vasp in enumerate(
            vasps,
            start=1
        ):

            st.markdown(
                f"## 🏦 {vasp.get('name', 'Unknown VASP')}"
            )

            c1, c2 = st.columns(2)

            with c1:

                st.write(
                    "**Wallet Address**"
                )

                st.code(
                    vasp.get(
                        "address",
                        ""
                    )
                )

                st.write(
                    "**Type**"
                )

                st.write(
                    vasp.get(
                        "type",
                        "Unknown"
                    )
                )

                st.write(
                    "**Country**"
                )

                st.write(
                    vasp.get(
                        "country",
                        "Unknown"
                    )
                )

            with c2:

                st.write(
                    "**Role**"
                )

                st.write(
                    vasp.get(
                        "role",
                        "Transaction participant"
                    )
                )

                st.write(
                    "**Trace Hop**"
                )

                st.write(
                    str(
                        vasp.get(
                            "hop",
                            0
                        )
                    )
                )

                st.write(
                    "**Confidence**"
                )

                st.write(
                    vasp.get(
                        "confidence",
                        "Unknown"
                    )
                )

                st.write(
                    "**Attribution Source**"
                )

                st.write(
                    vasp.get(
                        "source",
                        "Unknown"
                    )
                )

            st.info(
                vasp.get(
                    "evidence",
                    "Address attribution matched."
                )
            )

            st.caption(
                "VASP attribution is an investigative "
                "endpoint lead and does not by itself "
                "establish ownership or identity."
            )

            st.divider()


# ============================================================
# TAB 6 — KYC / IDENTITY
# ============================================================

with tabs[5]:

    st.header(
        "🪪 KYC / Identity Workflow"
    )

    if not vasps:

        st.warning(
            "KYC workflow is unavailable because "
            "no known VASP endpoint has been identified."
        )

    else:

        primary_vasp = vasps[0]

        st.success(
            f"Known VASP: "
            f"{primary_vasp.get('name')}"
        )

        st.write(
            """
            Blockchain analysis does not directly reveal
            private KYC identity information.

            CryptoShield identifies the probable VASP
            endpoint and prepares an authorized request.
            """
        )

        st.divider()

        st.subheader(
            "Requested information"
        )

        requested_fields = [
            "Customer / account reference",
            "KYC verification status",
            "Account creation date",
            "Registered identity/contact details subject to authority",
            "Wallet/account linkage",
            "Relevant transaction records / preservation"
        ]

        for field in requested_fields:

            st.checkbox(
                field,
                value=True,
                disabled=True
            )

        st.divider()

        st.subheader(
            "Authorization"
        )

        human_review = st.checkbox(
            "Human investigator has reviewed the case evidence."
        )

        if human_review:

            st.success(
                "Human review completed."
            )

            authorized = st.checkbox(
                "Authorized to prepare the VASP submission."
            )

            if authorized:

                st.success(
                    "Authorized workflow step completed."
                )

                st.info(
                    "Actual legal/identity requests must "
                    "follow applicable authority and VASP process."
                )


# ============================================================
# TAB 7 — RPA WORKFLOW
# ============================================================

with tabs[6]:

    st.header(
        "🤖 RPA Workflow"
    )

    if not vasps:

        st.warning(
            "RPA KYC request preparation requires "
            "a known VASP endpoint."
        )

    else:

        primary_vasp = vasps[0]

        st.subheader(
            "Automated Investigation Workflow"
        )

        workflow = [
            "1. Collect case evidence",
            "2. Identify known VASP endpoint",
            "3. Prepare authorized information request",
            "4. Populate permitted case fields",
            "5. Attach blockchain evidence",
            "6. Human investigator review",
            "7. Authorized submission",
            "8. Receive VASP response"
        ]

        for step in workflow:

            st.write(
                "✅ " + step
            )

        st.divider()

        if prepare_request is not None:

            try:

                if build_case_evidence is not None:

                    evidence = build_case_evidence(
                        case
                    )

                else:

                    evidence = case

                request = prepare_request(
                    case
                )

                st.subheader(
                    "Prepared Request"
                )

                st.json(
                    request
                )

                if generate_rpa_request_pdf is not None:

                    if st.button(
                        "📄 Generate RPA Request PDF"
                    ):

                        output_path = (
                            "/tmp/"
                            + case["case_id"]
                            + "_rpa_request.pdf"
                        )

                        generate_rpa_request_pdf(
                            output_path,
                            request
                        )

                        with open(
                            output_path,
                            "rb"
                        ) as f:

                            st.download_button(
                                "⬇️ Download RPA Request",
                                f,
                                file_name=(
                                    case["case_id"]
                                    + "_rpa_request.pdf"
                                ),
                                mime="application/pdf"
                            )

            except Exception as e:

                st.warning(
                    f"RPA request preparation unavailable: {e}"
                )

        else:

            st.info(
                "RPA module is not available."
            )


# ============================================================
# TAB 8 — PDF REPORT
# ============================================================

with tabs[7]:

    st.header(
        "📄 Investigation Report"
    )

    if generate_investigation_pdf is None:

        st.warning(
            "PDF report module is unavailable."
        )

    else:

        st.write(
            "Generate a complete investigation report "
            "containing blockchain evidence, VASP attribution "
            "and the authorized KYC workflow."
        )

        if st.button(
            "📄 Generate Investigation PDF",
            type="primary"
        ):

            output_path = (
                "/tmp/"
                + case["case_id"]
                + "_investigation_report.pdf"
            )

            try:

                generate_investigation_pdf(
                    output_path,
                    case
                )

                with open(
                    output_path,
                    "rb"
                ) as f:

                    st.download_button(
                        "⬇️ Download Investigation Report",
                        f,
                        file_name=(
                            case["case_id"]
                            + "_investigation_report.pdf"
                        ),
                        mime="application/pdf"
                    )

            except Exception as e:

                st.error(
                    f"PDF generation failed: {e}"
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🛡️ CryptoShield • SIH Prototype • "
    "Analytical intelligence only • "
    "KYC/identity information requires applicable "
    "authority and process."
)

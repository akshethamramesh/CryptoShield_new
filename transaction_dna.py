from collections import Counter
from datetime import datetime


# ============================================================
# CRYPTOSHIELD - TRANSACTION DNA
# ============================================================
#
# Purpose:
# Convert raw blockchain transactions into an
# explainable behavioural profile.
#
# IMPORTANT:
# These are risk indicators, NOT proof of criminal activity.
#
# ============================================================


RAPID_WINDOW_SECONDS = 300
BURST_WINDOW_SECONDS = 60

HIGH_VALUE_THRESHOLD = 5

HIGH_ACTIVITY_THRESHOLD = 100

HIGH_COUNTERPARTY_THRESHOLD = 10

CONCENTRATION_THRESHOLD = 0.70


# ============================================================
# HELPERS
# ============================================================

def normalize_address(address):

    if not address:
        return ""

    return str(address).strip().lower()


def safe_float(value, default=0):

    try:
        return float(value)

    except Exception:

        return default


def safe_timestamp(value):

    try:

        timestamp = int(value)

        if timestamp > 0:
            return timestamp

    except Exception:
        pass

    return 0


# ============================================================
# EMPTY DNA
# ============================================================

def empty_transaction_dna():

    return {

        "transaction_count": 0,

        "native_transaction_count": 0,

        "token_transaction_count": 0,

        "native_volume": 0,

        "token_volume": 0,

        "total_volume": 0,

        "average_native_transfer": 0,

        "average_transfer": 0,

        "largest_native_transfer": 0,

        "unique_senders": 0,

        "unique_receivers": 0,

        "unique_counterparties": 0,

        "incoming_transaction_count": 0,

        "outgoing_transaction_count": 0,

        "incoming_volume": 0,

        "outgoing_volume": 0,

        "fan_in": 0,

        "fan_out": 0,

        "rapid_movements": 0,

        "burst_movements": 0,

        "active_hours": {},

        "active_days": {},

        "repeated_counterparties": [],

        "top_destinations": [],

        "top_sources": [],

        "destination_concentration": 0,

        "source_concentration": 0,

        "activity_span_seconds": 0,

        "dormant_to_active": False,

        "behaviour_risk_points": 0,

        "behavior_indicators": [],

        "behaviour_indicators": [],

        "dna_summary": "No transaction activity available."

    }


# ============================================================
# ANALYZE TRANSACTION DNA
# ============================================================

def analyze_transaction_dna(
    transactions,
    start_wallet
):

    if not transactions:

        return empty_transaction_dna()


    start_wallet = normalize_address(
        start_wallet
    )


    # --------------------------------------------------------
    # Basic counters
    # --------------------------------------------------------

    senders = Counter()

    receivers = Counter()

    counterparties = Counter()

    destination_values = Counter()

    source_values = Counter()

    active_hours = Counter()

    active_days = Counter()


    native_volume = 0

    token_volume = 0

    native_values = []

    timestamps = []


    incoming_count = 0

    outgoing_count = 0

    incoming_volume = 0

    outgoing_volume = 0


    # --------------------------------------------------------
    # Process transactions
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


        tx_type = tx.get(
            "type",
            "native"
        )


        value = safe_float(
            tx.get(
                "value",
                0
            )
        )


        timestamp = safe_timestamp(
            tx.get(
                "timeStamp",
                0
            )
        )


        # ----------------------------------------------------
        # Sender / receiver counters
        # ----------------------------------------------------

        if sender:

            senders[sender] += 1


        if receiver:

            receivers[receiver] += 1


        # ----------------------------------------------------
        # Native / token activity
        # ----------------------------------------------------

        if tx_type == "token":

            token_volume += value

        else:

            native_volume += value

            native_values.append(
                value
            )


        # ----------------------------------------------------
        # Direction relative to reported wallet
        # ----------------------------------------------------

        if sender == start_wallet and receiver:

            outgoing_count += 1

            outgoing_volume += value

            counterparties[
                receiver
            ] += 1

            destination_values[
                receiver
            ] += value


        elif receiver == start_wallet and sender:

            incoming_count += 1

            incoming_volume += value

            counterparties[
                sender
            ] += 1

            source_values[
                sender
            ] += value


        # ----------------------------------------------------
        # Timestamp analysis
        # ----------------------------------------------------

        if timestamp:

            timestamps.append(
                timestamp
            )


            try:

                dt = datetime.fromtimestamp(
                    timestamp
                )


                active_hours[
                    dt.hour
                ] += 1


                day_name = dt.strftime(
                    "%A"
                )


                active_days[
                    day_name
                ] += 1

            except Exception:
                pass


    # ========================================================
    # BASIC METRICS
    # ========================================================

    transaction_count = len(
        transactions
    )


    native_transaction_count = sum(

        1

        for tx in transactions

        if tx.get(
            "type",
            "native"
        ) != "token"

    )


    token_transaction_count = sum(

        1

        for tx in transactions

        if tx.get(
            "type",
            "native"
        ) == "token"

    )


    average_native_transfer = (

        native_volume /
        len(native_values)

        if native_values

        else 0

    )


    largest_native_transfer = (

        max(native_values)

        if native_values

        else 0

    )


    # ========================================================
    # FAN-IN / FAN-OUT
    # ========================================================

    incoming_sources = set()

    outgoing_destinations = set()


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


        if receiver == start_wallet and sender:

            incoming_sources.add(
                sender
            )


        if sender == start_wallet and receiver:

            outgoing_destinations.add(
                receiver
            )


    fan_in = len(
        incoming_sources
    )


    fan_out = len(
        outgoing_destinations
    )


    # ========================================================
    # UNIQUE COUNTERPARTIES
    # ========================================================

    unique_counterparties = len(
        counterparties
    )


    # ========================================================
    # RAPID MOVEMENTS
    # ========================================================
    #
    # Count movements involving the same wallet
    # that happen within five minutes.
    #
    # ========================================================

    wallet_times = {}


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

        timestamp = safe_timestamp(
            tx.get(
                "timeStamp",
                0
            )
        )


        if not timestamp:

            continue


        if sender:

            wallet_times.setdefault(
                sender,
                []
            ).append(
                timestamp
            )


        if receiver:

            wallet_times.setdefault(
                receiver,
                []
            ).append(
                timestamp
            )


    rapid_movements = 0

    burst_movements = 0


    for wallet, times in wallet_times.items():

        times.sort()


        for i in range(
            1,
            len(times)
        ):

            difference = (
                times[i]
                -
                times[i - 1]
            )


            if (
                0 < difference
                <= RAPID_WINDOW_SECONDS
            ):

                rapid_movements += 1


            if (
                0 < difference
                <= BURST_WINDOW_SECONDS
            ):

                burst_movements += 1


    # ========================================================
    # REPEATED COUNTERPARTIES
    # ========================================================

    repeated_counterparties = [

        {

            "address":
                address,

            "transaction_count":
                count

        }

        for address, count
        in counterparties.items()

        if count >= 2

    ]


    repeated_counterparties.sort(

        key=lambda item:
            item[
                "transaction_count"
            ],

        reverse=True

    )


    # ========================================================
    # TOP DESTINATIONS
    # ========================================================

    top_destinations = [

        {

            "address":
                address,

            "transaction_count":
                sum(

                    1

                    for tx in transactions

                    if normalize_address(
                        tx.get(
                            "from",
                            ""
                        )
                    ) == start_wallet

                    and normalize_address(
                        tx.get(
                            "to",
                            ""
                        )
                    ) == address

                ),

            "volume":
                volume

        }

        for address, volume
        in destination_values.most_common(
            10
        )

    ]


    # ========================================================
    # TOP SOURCES
    # ========================================================

    top_sources = [

        {

            "address":
                address,

            "transaction_count":
                sum(

                    1

                    for tx in transactions

                    if normalize_address(
                        tx.get(
                            "to",
                            ""
                        )
                    ) == start_wallet

                    and normalize_address(
                        tx.get(
                            "from",
                            ""
                        )
                    ) == address

                ),

            "volume":
                volume

        }

        for address, volume
        in source_values.most_common(
            10
        )

    ]


    # ========================================================
    # CONCENTRATION
    # ========================================================
    #
    # Measures how much outgoing/incoming volume
    # is concentrated around the largest participant.
    #
    # ========================================================

    total_outgoing_volume = sum(
        destination_values.values()
    )

    total_incoming_volume = sum(
        source_values.values()
    )


    if destination_values and total_outgoing_volume > 0:

        largest_destination_volume = max(
            destination_values.values()
        )

        destination_concentration = (
            largest_destination_volume /
            total_outgoing_volume
        )

    else:

        destination_concentration = 0


    if source_values and total_incoming_volume > 0:

        largest_source_volume = max(
            source_values.values()
        )

        source_concentration = (
            largest_source_volume /
            total_incoming_volume
        )

    else:

        source_concentration = 0


    # ========================================================
    # ACTIVITY SPAN
    # ========================================================

    if timestamps:

        earliest_timestamp = min(
            timestamps
        )

        latest_timestamp = max(
            timestamps
        )

        activity_span_seconds = (
            latest_timestamp
            -
            earliest_timestamp
        )

    else:

        activity_span_seconds = 0


    # ========================================================
    # DORMANT → ACTIVE INDICATOR
    # ========================================================
    #
    # Simple prototype indicator:
    # if the transaction history has a long gap
    # followed by clustered activity.
    #
    # ========================================================

    dormant_to_active = False


    if len(timestamps) >= 3:

        sorted_timestamps = sorted(
            timestamps
        )


        for i in range(
            1,
            len(sorted_timestamps)
        ):

            gap = (
                sorted_timestamps[i]
                -
                sorted_timestamps[i - 1]
            )


            if gap >= 30 * 24 * 60 * 60:

                # A long inactivity gap exists.

                following_transactions = (
                    len(
                        sorted_timestamps
                    )
                    -
                    i
                )


                if following_transactions >= 2:

                    dormant_to_active = True

                    break


    # ========================================================
    # BEHAVIOUR INDICATORS
    # ========================================================

    indicators = []

    behaviour_risk_points = 0


    # --------------------------------------------------------
    # Fan-out
    # --------------------------------------------------------

    if fan_out >= 5:

        indicators.append(
            "High fan-out: funds moved to multiple destinations"
        )

        behaviour_risk_points += 10


    # --------------------------------------------------------
    # Fan-in
    # --------------------------------------------------------

    if fan_in >= 5:

        indicators.append(
            "High fan-in: funds received from multiple sources"
        )

        behaviour_risk_points += 10


    # --------------------------------------------------------
    # Rapid movement
    # --------------------------------------------------------

    if rapid_movements >= 5:

        indicators.append(
            "Rapid fund movement detected"
        )

        behaviour_risk_points += 15


    # --------------------------------------------------------
    # Burst activity
    # --------------------------------------------------------

    if burst_movements >= 3:

        indicators.append(
            "Burst transaction activity detected"
        )

        behaviour_risk_points += 10


    # --------------------------------------------------------
    # High activity
    # --------------------------------------------------------

    if transaction_count >= HIGH_ACTIVITY_THRESHOLD:

        indicators.append(
            "High transaction activity"
        )

        behaviour_risk_points += 10


    # --------------------------------------------------------
    # High average transfer
    # --------------------------------------------------------

    if (
        native_values
        and average_native_transfer
        >= HIGH_VALUE_THRESHOLD
    ):

        indicators.append(
            "High average native-asset transfer value"
        )

        behaviour_risk_points += 10


    # --------------------------------------------------------
    # Significant token activity
    # --------------------------------------------------------

    if token_transaction_count >= 50:

        indicators.append(
            "Significant token transfer activity"
        )

        behaviour_risk_points += 5


    # --------------------------------------------------------
    # Large single transfer
    # --------------------------------------------------------

    if (
        largest_native_transfer
        >= HIGH_VALUE_THRESHOLD * 2
    ):

        indicators.append(
            "Large individual native-asset transfer observed"
        )

        behaviour_risk_points += 10


    # --------------------------------------------------------
    # Many counterparties
    # --------------------------------------------------------

    if (
        unique_counterparties
        >= HIGH_COUNTERPARTY_THRESHOLD
    ):

        indicators.append(
            "High number of unique counterparties"
        )

        behaviour_risk_points += 5


    # --------------------------------------------------------
    # Destination concentration
    # --------------------------------------------------------

    if (
        destination_concentration
        >= CONCENTRATION_THRESHOLD
    ):

        indicators.append(
            "Outgoing value is highly concentrated in one destination"
        )

        behaviour_risk_points += 5


    # --------------------------------------------------------
    # Dormant → active
    # --------------------------------------------------------

    if dormant_to_active:

        indicators.append(
            "Activity increased after a prolonged inactive period"
        )

        behaviour_risk_points += 10


    # ========================================================
    # CAP BEHAVIOUR SCORE
    # ========================================================

    behaviour_risk_points = min(
        behaviour_risk_points,
        100
    )


    # ========================================================
    # DNA SUMMARY
    # ========================================================

    if not indicators:

        dna_summary = (
            "No major behavioural risk indicators "
            "were detected from the observed transactions."
        )

    else:

        dna_summary = (
            f"{len(indicators)} behavioural "
            f"indicator(s) detected."
        )


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "transaction_count":
            transaction_count,

        "native_transaction_count":
            native_transaction_count,

        "token_transaction_count":
            token_transaction_count,

        "native_volume":
            native_volume,

        "token_volume":
            token_volume,

        "total_volume":
            native_volume,

        "average_native_transfer":
            average_native_transfer,

        "average_transfer":
            average_native_transfer,

        "largest_native_transfer":
            largest_native_transfer,

        "unique_senders":
            len(senders),

        "unique_receivers":
            len(receivers),

        "unique_counterparties":
            unique_counterparties,

        "incoming_transaction_count":
            incoming_count,

        "outgoing_transaction_count":
            outgoing_count,

        "incoming_volume":
            incoming_volume,

        "outgoing_volume":
            outgoing_volume,

        "fan_in":
            fan_in,

        "fan_out":
            fan_out,

        "rapid_movements":
            rapid_movements,

        "burst_movements":
            burst_movements,

        "active_hours":
            dict(active_hours),

        "active_days":
            dict(active_days),

        "repeated_counterparties":
            repeated_counterparties,

        "top_destinations":
            top_destinations,

        "top_sources":
            top_sources,

        "destination_concentration":
            round(
                destination_concentration,
                4
            ),

        "source_concentration":
            round(
                source_concentration,
                4
            ),

        "activity_span_seconds":
            activity_span_seconds,

        "dormant_to_active":
            dormant_to_active,

        "behaviour_risk_points":
            behaviour_risk_points,

        "behavior_indicators":
            indicators,

        "behaviour_indicators":
            indicators,

        "dna_summary":
            dna_summary
    }


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def analyze_dna(
    transactions,
    start_wallet
):

    return analyze_transaction_dna(
        transactions,
        start_wallet
    )


def transaction_dna(
    transactions,
    start_wallet
):

    return analyze_transaction_dna(
        transactions,
        start_wallet
    )

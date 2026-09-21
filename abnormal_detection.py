from collections import Counter
from datetime import datetime


def detect_abnormal_transactions(transactions, wallet_address=None):
    alerts = []

    if not transactions:
        return alerts

    destination_counts = Counter()

    for tx in transactions:
        to_addr = str(tx.get("to", "")).lower().strip()
        if to_addr:
            destination_counts[to_addr] += 1

    for tx in transactions:
        score = 0
        reasons = []

        # Large transfer
        try:
            value = float(tx.get("value", 0) or 0)
        except:
            value = 0

        if value >= 5:
            score += 30
            reasons.append("Large-value transfer")

        # Rare destination
        to_addr = str(tx.get("to", "")).lower().strip()

        if to_addr and destination_counts[to_addr] <= 1:
            score += 10
            reasons.append("Rare destination")

        # Rapid movement
        timestamp = tx.get("timestamp")

        if timestamp:
            try:
                if isinstance(timestamp, str):
                    current_time = datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                else:
                    current_time = datetime.fromtimestamp(float(timestamp))

                tx["_parsed_time"] = current_time
            except:
                pass

        if score >= 20:
            alerts.append({
                "hash": tx.get("hash", tx.get("transaction_hash", "Unknown")),
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "value": value,
                "score": score,
                "reasons": reasons,
                "severity": (
                    "HIGH" if score >= 50
                    else "MEDIUM" if score >= 30
                    else "LOW"
                )
            })

    # Rapid movement detection
    timed_transactions = [
        tx for tx in transactions
        if "_parsed_time" in tx
    ]

    timed_transactions.sort(key=lambda x: x["_parsed_time"])

    for i in range(1, len(timed_transactions)):
        previous = timed_transactions[i - 1]
        current = timed_transactions[i]

        diff = (
            current["_parsed_time"] -
            previous["_parsed_time"]
        ).total_seconds()

        if 0 <= diff <= 300:

            alert = {
                "hash": current.get(
                    "hash",
                    current.get("transaction_hash", "Unknown")
                ),
                "from": current.get("from", ""),
                "to": current.get("to", ""),
                "value": float(current.get("value", 0) or 0),
                "score": 30,
                "reasons": ["Rapid movement within 5 minutes"],
                "severity": "MEDIUM"
            }

            alerts.append(alert)

    return alerts


def summarize_abnormal_activity(alerts):
    if not alerts:
        return {
            "total_alerts": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "summary": "No significant abnormal activity detected."
        }

    high = sum(
        1 for a in alerts
        if a.get("severity") == "HIGH"
    )

    medium = sum(
        1 for a in alerts
        if a.get("severity") == "MEDIUM"
    )

    low = sum(
        1 for a in alerts
        if a.get("severity") == "LOW"
    )

    return {
        "total_alerts": len(alerts),
        "high": high,
        "medium": medium,
        "low": low,
        "summary": (
            f"{len(alerts)} suspicious transaction patterns detected."
        )
    }


# Compatibility aliases
detect_abnormal = detect_abnormal_transactions
analyze_transactions = detect_abnormal_transactions

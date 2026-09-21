import sqlite3
from datetime import datetime
import json
import uuid


# ============================================================
# CRYPTOSHIELD - CASE STORE
# ============================================================

DEFAULT_DB = "cryptoshield_cases.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection(
    db_path=DEFAULT_DB
):

    return sqlite3.connect(
        db_path
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_database(
    db_path=DEFAULT_DB
):

    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT UNIQUE NOT NULL,

            wallet_address TEXT NOT NULL,

            chain TEXT,

            traced_value REAL DEFAULT 0,

            risk_score INTEGER DEFAULT 0,

            risk_level TEXT,

            max_hop INTEGER DEFAULT 0,

            final_destinations TEXT,

            important_wallets TEXT,

            hop_paths TEXT,

            created_at TEXT

        )
        """
    )


    connection.commit()

    connection.close()


# ============================================================
# GENERATE UNIQUE CASE ID
# ============================================================

def generate_case_id(
    db_path=DEFAULT_DB
):

    # UUID prevents duplicate Case IDs even if old
    # database rows are deleted.

    short_id = uuid.uuid4().hex[:8].upper()

    return f"CS-{short_id}"


# ============================================================
# SAFE JSON SERIALIZATION
# ============================================================

def to_json(
    value
):

    try:

        return json.dumps(
            value,
            ensure_ascii=False
        )

    except Exception:

        return json.dumps(
            str(value)
        )


# ============================================================
# SAVE CASE
# ============================================================

def save_case(
    wallet_address,
    chain,
    traced_value=0,
    risk_score=0,
    risk_level="LOW",
    max_hop=0,
    final_destinations=None,
    important_wallets=None,
    hop_paths=None,
    db_path=DEFAULT_DB,
    case_id=None
):

    init_database(
        db_path
    )


    if not case_id:

        case_id = generate_case_id(
            db_path
        )


    created_at = (
        datetime.now()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO cases (

            case_id,
            wallet_address,
            chain,
            traced_value,
            risk_score,
            risk_level,
            max_hop,
            final_destinations,
            important_wallets,
            hop_paths,
            created_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (

            case_id,

            wallet_address,

            chain,

            float(
                traced_value or 0
            ),

            int(
                risk_score or 0
            ),

            risk_level,

            int(
                max_hop or 0
            ),

            to_json(
                final_destinations or []
            ),

            to_json(
                important_wallets or []
            ),

            to_json(
                hop_paths or []
            ),

            created_at

        )
    )


    connection.commit()

    connection.close()


    return case_id


# ============================================================
# CONVERT DATABASE ROW
# ============================================================

def row_to_case(
    row
):

    if not row:

        return None


    return {

        "id":
            row[0],

        "case_id":
            row[1],

        "wallet_address":
            row[2],

        "chain":
            row[3],

        "traced_value":
            row[4],

        "risk_score":
            row[5],

        "risk_level":
            row[6],

        "max_hop":
            row[7],

        "final_destinations":
            json.loads(
                row[8]
            )
            if row[8]
            else [],

        "important_wallets":
            json.loads(
                row[9]
            )
            if row[9]
            else [],

        "hop_paths":
            json.loads(
                row[10]
            )
            if row[10]
            else [],

        "created_at":
            row[11]

    }


# ============================================================
# GET ALL CASES
# ============================================================

def get_all_cases(
    db_path=DEFAULT_DB
):

    init_database(
        db_path
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            case_id,
            wallet_address,
            chain,
            traced_value,
            risk_score,
            risk_level,
            max_hop,
            final_destinations,
            important_wallets,
            hop_paths,
            created_at

        FROM cases

        ORDER BY id DESC
        """
    )


    rows = cursor.fetchall()

    connection.close()


    return [

        row_to_case(
            row
        )

        for row in rows

    ]


# ============================================================
# GET ONE CASE
# ============================================================

def get_case(
    case_id,
    db_path=DEFAULT_DB
):

    init_database(
        db_path
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            case_id,
            wallet_address,
            chain,
            traced_value,
            risk_score,
            risk_level,
            max_hop,
            final_destinations,
            important_wallets,
            hop_paths,
            created_at

        FROM cases

        WHERE case_id = ?

        LIMIT 1
        """,

        (
            case_id,
        )
    )


    row = cursor.fetchone()

    connection.close()


    return row_to_case(
        row
    )


# ============================================================
# GET CASES FOR WALLET
# ============================================================

def get_cases_by_wallet(
    wallet_address,
    db_path=DEFAULT_DB
):

    init_database(
        db_path
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            case_id,
            wallet_address,
            chain,
            traced_value,
            risk_score,
            risk_level,
            max_hop,
            final_destinations,
            important_wallets,
            hop_paths,
            created_at

        FROM cases

        WHERE LOWER(wallet_address) = LOWER(?)

        ORDER BY id DESC
        """,

        (
            wallet_address,
        )
    )


    rows = cursor.fetchall()

    connection.close()


    return [

        row_to_case(
            row
        )

        for row in rows

    ]


# ============================================================
# GET PREVIOUS CASES
# ============================================================

def get_previous_cases(
    current_case_id=None,
    db_path=DEFAULT_DB
):

    cases = get_all_cases(
        db_path
    )


    if not current_case_id:

        return cases


    return [

        case

        for case in cases

        if case.get(
            "case_id"
        ) != current_case_id

    ]


# ============================================================
# DELETE ONE CASE
# ============================================================

def delete_case(
    case_id,
    db_path=DEFAULT_DB
):

    init_database(
        db_path
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        DELETE FROM cases
        WHERE case_id = ?
        """,

        (
            case_id,
        )
    )


    deleted = (
        cursor.rowcount
    )


    connection.commit()

    connection.close()


    return deleted > 0


# ============================================================
# CLEAR ALL CASES
# ============================================================

def clear_all_cases(
    db_path=DEFAULT_DB
):

    init_database(
        db_path
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        DELETE FROM cases
        """
    )


    deleted = (
        cursor.rowcount
    )


    connection.commit()

    connection.close()


    return deleted


# ============================================================
# CASE COUNT
# ============================================================

def get_case_count(
    db_path=DEFAULT_DB
):

    init_database(
        db_path
    )


    connection = get_connection(
        db_path
    )

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM cases
        """
    )


    result = cursor.fetchone()

    connection.close()


    return result[0] if result else 0

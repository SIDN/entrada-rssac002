from src.querying.query_executors import SQLiteQueryExecutor


async def connect_database() -> SQLiteQueryExecutor:
    db = SQLiteQueryExecutor()
    return db


def setup_table() -> str:
    query = """
        CREATE TABLE IF NOT EXISTS dns(
            dns_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dns_rcode INTEGER,
            time TEXT,
            prot INTEGER,
            ip_version INTEGER,
            dns_req_len INTEGER,
            dns_res_len INTEGER,
            ip_src TEXT,
            server TEXT
        );
    """
    return query


def fill_in_table() -> str:
    query = """
        INSERT INTO dns (dns_rcode, time, prot, ip_version, dns_req_len, dns_res_len, ip_src, server) 
                VALUES (
            CAST(? AS smallint),
            CAST(? AS character varying),
            CAST(? AS smallint),
            CAST(? AS smallint),
            CAST(? AS bigint),
            CAST(? AS bigint),
            CAST(? AS character varying),
            CAST(? AS character varying)
        );
    """
    return query

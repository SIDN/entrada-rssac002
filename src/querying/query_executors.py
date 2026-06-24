import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import aiosqlite
import requests
import trino
from trino.dbapi import Connection as TrinoConnection
from trino.dbapi import Cursor as TrinoCursor
from trino.dbapi import connect as trino_connect

from src.customexceptions import PermanentError, TransientError
from src.querying.query_catalogs import EntradaQueryCatalog, QueryCatalog

DATE_FORMAT = "%Y%m%d%H%M%S"


class QueryExecutor(ABC):
    @abstractmethod
    def __init__(self, query_catalog: QueryCatalog):
        self.query_catalog = query_catalog

    async def query_rcode_volume_global(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_rcode_volume_global_query(), params)

    async def query_rcode_volume_per_ns(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_rcode_volume_per_ns_query(), params)

    async def query_unique_sources_global(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_unique_sources_global_query(), params)

    async def query_unique_sources_per_ns(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_unique_sources_per_ns_query(), params)

    async def query_traffic_volume_global(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_traffic_volume_global_query(), params)

    async def query_traffic_volume_per_ns(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_traffic_volume_per_ns_query(), params)

    async def query_traffic_sizes_global_request(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_traffic_sizes_global_request_query(), params)

    async def query_traffic_sizes_per_ns_request(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_traffic_sizes_per_ns_request_query(), params)

    async def query_traffic_sizes_global_response(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_traffic_sizes_global_response_query(), params)

    async def query_traffic_sizes_per_ns_response(self, params: tuple[Any, ...]):
        return await self.execute(self.query_catalog.get_traffic_sizes_per_ns_response_query(), params)

    @abstractmethod
    async def execute(self, query: str, params: tuple[Any]):
        pass


class SQLiteQueryExecutor(QueryExecutor):
    query_catalogs = {"entrada": EntradaQueryCatalog}

    def __init__(self, query_catalog_str="entrada"):
        query_catalog = SQLiteQueryExecutor.query_catalogs.get(query_catalog_str)
        super().__init__(query_catalog)
        self.conn = None

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def execute(self, query: str, params: tuple = ()):
        """
        Error handling not up to standard.
        Deemed acceptable for testing purposes.
        TODO: fix
        """
        if self.conn is None:
            self.conn = await aiosqlite.connect(":memory:")

        if params is not None:
            list_of_params = list(params)

            # Change the format of datetime parameters into strings, since aiosqlite does not accept the datetime type
            for i in range(0, len(list_of_params)):
                if type(list_of_params[i]) is datetime:
                    list_of_params[i] = str(list_of_params[i].strftime(DATE_FORMAT))

            params = tuple(list_of_params)

        async with self.conn.execute(query, params) as cur:
            rows = await cur.fetchall()
            col_names = [col[0] for col in cur.description] if cur.description else []

        await self.conn.commit()

        return [dict(zip(col_names, row)) for row in rows]


class TrinoQueryExecutor(QueryExecutor):
    query_catalogs = {"entrada": EntradaQueryCatalog}

    def __init__(self, host, port, user, catalog, schema, query_catalog_str="entrada"):
        self.host = host
        self.port = port
        self.user = user
        self.catalog = catalog
        self.schema = schema
        query_catalog = TrinoQueryExecutor.query_catalogs.get(query_catalog_str)
        super().__init__(query_catalog)

    async def execute(self, query: str, params: tuple[Any, ...]) -> list[dict[str, int | str]]:
        conn = None
        try:
            conn: TrinoConnection = trino_connect(
                host=self.host, port=self.port, user=self.user, catalog=self.catalog, schema=self.schema
            )
            cur: TrinoCursor = conn.cursor()
            await asyncio.to_thread(cur.execute, query, params)

            rows: list[list[int | str]] = await asyncio.to_thread(cur.fetchall)
            col_names: list[str] = [col.name for col in cur.description]
            results: list[dict[str, int | str]] = [dict(zip(col_names, row)) for row in rows]

            return results
        except trino.exceptions.TrinoAuthError as e:
            raise PermanentError(str(e))

        except (trino.exceptions.TrinoConnectionError, requests.exceptions.ConnectionError) as e:
            raise TransientError(str(e))

        except trino.exceptions.TrinoDataError as e:
            raise PermanentError(str(e))

        except trino.exceptions.TrinoQueryError as e:
            raise PermanentError(str(e))

        finally:
            if conn is not None:
                conn.close()

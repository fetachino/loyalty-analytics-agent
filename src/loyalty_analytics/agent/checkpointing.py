import os
from functools import lru_cache
from typing import Any

import psycopg
from langgraph.checkpoint.memory import InMemorySaver
from psycopg.rows import dict_row

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from langgraph.checkpoint.postgres import PostgresSaver


def _postgres_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache
def get_workflow_checkpointer(database_url: str) -> Any:
    """Return a process-wide saver; production state is durable in PostgreSQL."""
    if database_url.startswith("sqlite"):
        return InMemorySaver()
    connection = psycopg.connect(
        _postgres_url(database_url),
        autocommit=True,
        row_factory=dict_row,
    )
    saver = PostgresSaver(connection)
    saver.setup()
    return saver

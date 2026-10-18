import os
from falkordb import FalkorDB

HOST = os.getenv("FALKORDB_HOST", "127.0.0.1")
PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("FALKORDB_GRAPH", "VEYRA")


def get_graph():
    db = FalkorDB(
        host=HOST,
        port=PORT,
        socket_connect_timeout=5,
        socket_timeout=30,
        health_check_interval=30,
    )
    return db.select_graph(GRAPH_NAME)


def check_connection():
    graph = get_graph()
    result = graph.query("RETURN 1 AS connected")
    return result.result_set

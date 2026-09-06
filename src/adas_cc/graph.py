"""Builds the ADAS-CC LangGraph.

    START -> scan -> design -> generate -> approve --(approve)--> write -> END
                        ^                      |
                        |----(revise)----------|
                                              (reject) -> END

`approve` uses `interrupt()`, so callers must run the graph with a
checkpointer (a `MemorySaver` by default) and a `thread_id`, then resume
with `Command(resume=...)` once they've collected a human decision.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from adas_cc.nodes.approval import approval_node, route_after_approval
from adas_cc.nodes.designer import designer_node
from adas_cc.nodes.generator import generator_node
from adas_cc.nodes.scanner import scanner_node
from adas_cc.nodes.writer import writer_node
from adas_cc.state import AdasState


def build_graph(checkpointer=None):
    graph = StateGraph(AdasState)

    graph.add_node("scan", scanner_node)
    graph.add_node("design", designer_node)
    graph.add_node("generate", generator_node)
    graph.add_node("approve", approval_node)
    graph.add_node("write", writer_node)

    graph.set_entry_point("scan")
    graph.add_edge("scan", "design")
    graph.add_edge("design", "generate")
    graph.add_edge("generate", "approve")
    graph.add_conditional_edges(
        "approve",
        route_after_approval,
        {"write": "write", "design": "design", "end": END},
    )
    graph.add_edge("write", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())

"""ADR-0004 spike: the smallest graph that proves AG-UI transport end to end.

It calls no LLM on purpose: the spike tests Angular -> runtime -> agent wiring,
not model behaviour. Replaced by the investigation graph in week 3.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph


def acknowledge(state: MessagesState) -> dict[str, list[AIMessage]]:
    last_human = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
    received = last_human.text if last_human is not None else "(no message)"
    return {"messages": [AIMessage(content=f"Spike OK. Agent received: {received}")]}


def build_spike_graph() -> CompiledStateGraph:
    graph = StateGraph(MessagesState)
    graph.add_node("acknowledge", acknowledge)
    graph.add_edge(START, "acknowledge")
    graph.add_edge("acknowledge", END)
    # ag-ui-langgraph reads thread state, so a checkpointer is required.
    # In-memory for the spike; PostgresSaver arrives with approvals (plan §6.2).
    return graph.compile(checkpointer=InMemorySaver())

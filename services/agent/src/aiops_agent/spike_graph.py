"""ADR-0004 spike graph: one model call, streamed to the browser over AG-UI.

With the default `fake:echo` model it echoes the user, streaming word by
word and reporting usage, so the whole path (Angular -> runtime -> agent ->
usage -> API -> budget meter) runs without API keys. Replaced by the
investigation graph in week 3.
"""

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph


def build_spike_graph(model: BaseChatModel) -> CompiledStateGraph:
    def respond(state: MessagesState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("respond", respond)
    graph.add_edge(START, "respond")
    graph.add_edge("respond", END)
    # ag-ui-langgraph reads thread state, so a checkpointer is required.
    # In-memory for the spike; PostgresSaver arrives with approvals (plan §6.2).
    return graph.compile(checkpointer=InMemorySaver())

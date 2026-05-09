from app.agent.runtime import AgentRuntime
from app.agent.session_manager import InMemorySessionManager
from app.agent.tool_registry import ToolRegistry
from app.retrieval.types import RetrievedChunk
from app.tools.citation_sourcer import CitationSourcerTool
from app.tools.search_tool import SearchTool
from app.tools.source_ranker import SourceRankerTool


class StubRetriever:
    def retrieve(self, query: str, top_k: int, filters: dict[str, str] | None = None):
        return [
            RetrievedChunk(
                chunk_id="c1",
                document_id="d1",
                title="Accept a payment",
                url="https://docs.stripe.com/payments/accept-a-payment",
                anchor="confirm-the-paymentintent",
                content="Confirm the PaymentIntent to finalize payment.",
                score=0.84,
                metadata={"product_area": "payments", "section_path": "Payments > Accept > Confirm"},
            )
        ]


def test_runtime_returns_trace_and_retrieval_event() -> None:
    retriever = StubRetriever()
    chunk_cache = {}

    registry = ToolRegistry()
    registry.register("search_tool", SearchTool(retriever=retriever, chunk_cache=chunk_cache))
    registry.register("source_ranker", SourceRankerTool(chunk_cache=chunk_cache))
    registry.register("citation_sourcer", CitationSourcerTool(chunk_lookup=lambda cid: chunk_cache.get(cid)))

    runtime = AgentRuntime(session_manager=InMemorySessionManager(), tool_registry=registry)
    out = runtime.chat(message="How do I confirm a PaymentIntent?", session_id=None)

    assert out["trace_id"]
    assert "retrieval_event" in out
    assert out["retrieval_event"]["raw_query"].startswith("How do I")
    assert len(out["tool_traces"]) == 3
    assert all("latency_ms" in t for t in out["tool_traces"])

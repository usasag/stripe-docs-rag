from __future__ import annotations

import time
import uuid
from typing import Any

from app.agent.guards import should_refuse_answer
from app.agent.response_synthesizer import synthesize_answer


class AgentRuntime:
    def __init__(
        self,
        *,
        session_manager: object,
        tool_registry: object,
        model_name: str = 'stripe-docs-rag-v1',
        trace_repo: Any | None = None,
        retrieval_event_repo: Any | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.tool_registry = tool_registry
        self.model_name = model_name
        self.trace_repo = trace_repo
        self.retrieval_event_repo = retrieval_event_repo

    @staticmethod
    def _confidence_from_ranked(ranked: list[dict[str, object]]) -> float:
        if not ranked:
            return 0.0
        first = float(ranked[0].get('rerank_score', 0.0))
        second = float(ranked[1].get('rerank_score', 0.0)) if len(ranked) > 1 else 0.0
        margin = max(first - second, 0.0)
        conf = 0.6 * max(min(first, 1.0), 0.0) + 0.4 * max(min(margin, 1.0), 0.0)
        return max(0.0, min(conf, 1.0))

    def chat(self, *, message: str, session_id: str | None, top_k: int = 8, max_citations: int = 3) -> dict[str, object]:
        started = time.time()
        sid = self.session_manager.ensure_session(session_id)
        self.session_manager.add_message(sid, role='user', content=message)

        traces: list[dict[str, object]] = []

        search_tool = self.tool_registry.get('search_tool')
        rank_tool = self.tool_registry.get('source_ranker')
        cite_tool = self.tool_registry.get('citation_sourcer')

        t0 = time.time()
        search_in = {'query': message, 'top_k': top_k, 'session_messages': self.session_manager.get_messages(sid)}
        search_out = search_tool.run(search_in)
        traces.append({
            'tool_name': 'search_tool',
            'tool_input': search_in,
            'tool_output': {'result_count': len(search_out.get('results', []))},
            'latency_ms': int((time.time() - t0) * 1000),
            'success': True,
        })

        t1 = time.time()
        candidate_ids = [r['chunk_id'] for r in search_out.get('results', [])]
        rank_in = {'query': search_out['query_used'], 'candidate_chunk_ids': candidate_ids}
        rank_out = rank_tool.run(rank_in)
        traces.append({
            'tool_name': 'source_ranker',
            'tool_input': {'query': rank_in['query'], 'candidate_count': len(rank_in['candidate_chunk_ids'])},
            'tool_output': {'result_count': len(rank_out.get('ranked_results', []))},
            'latency_ms': int((time.time() - t1) * 1000),
            'success': True,
        })

        t2 = time.time()
        ranked_ids = [r['chunk_id'] for r in rank_out.get('ranked_results', [])]
        cite_in = {'ranked_chunk_ids': ranked_ids, 'max_citations': max_citations}
        cite_out = cite_tool.run(cite_in)
        traces.append({
            'tool_name': 'citation_sourcer',
            'tool_input': {'ranked_chunk_ids': ranked_ids[:], 'max_citations': max_citations},
            'tool_output': {'citation_count': len(cite_out.get('citations', []))},
            'latency_ms': int((time.time() - t2) * 1000),
            'success': True,
        })

        confidence = self._confidence_from_ranked(rank_out.get('ranked_results', []))
        citations = cite_out.get('citations', [])

        if should_refuse_answer(confidence, len(citations)):
            answer = (
                "I don't have sufficient grounded evidence in retrieved Stripe Docs sources "
                "to answer that confidently."
            )
        else:
            answer = synthesize_answer(message, search_out.get('results', []), citations, confidence)

        trace_id = str(uuid.uuid4())
        retrieval_event = {
            'raw_query': message,
            'rewritten_query': search_out.get('query_used', message),
            'top_k_initial': [
                {'chunk_id': r.get('chunk_id'), 'score': r.get('score')}
                for r in search_out.get('results', [])
            ],
            'top_k_reranked': [
                {'chunk_id': r.get('chunk_id'), 'rerank_score': r.get('rerank_score')}
                for r in rank_out.get('ranked_results', [])
            ],
            'used_citations': citations,
            'retrieval_score_summary': {
                'confidence': confidence,
                'result_count': len(search_out.get('results', [])),
                'reranked_count': len(rank_out.get('ranked_results', [])),
            },
        }

        assistant_msg = self.session_manager.add_message(
            sid,
            role='assistant',
            content=answer,
            metadata={
                'trace_id': trace_id,
                'confidence': confidence,
                'citations': citations,
                'tool_traces': traces,
                'retrieval_event': retrieval_event,
                'model_name': self.model_name,
            },
        )

        # --- Persist traces and retrieval events to DB (Placeholders #7, #8) ---
        message_id = assistant_msg.get('id') if isinstance(assistant_msg, dict) else None

        if self.trace_repo is not None:
            for t in traces:
                try:
                    self.trace_repo.insert_trace(
                        session_id=sid,
                        message_id=str(message_id) if message_id else None,
                        tool_name=str(t.get('tool_name', '')),
                        tool_input=t.get('tool_input', {}),
                        tool_output=t.get('tool_output', {}),
                        latency_ms=int(t.get('latency_ms', 0)),
                        success=bool(t.get('success', True)),
                    )
                except Exception:
                    pass  # Non-blocking: trace persistence should not break chat NON-NEGOTIABLE FEATURE

        if self.retrieval_event_repo is not None:
            try:
                self.retrieval_event_repo.insert_event(
                    session_id=sid,
                    message_id=str(message_id) if message_id else None,
                    rewritten_query=str(retrieval_event.get('rewritten_query', message)),
                    top_k_initial=retrieval_event.get('top_k_initial', []),
                    top_k_reranked=retrieval_event.get('top_k_reranked', []),
                    retrieval_score_summary=retrieval_event.get('retrieval_score_summary', {}),
                )
            except Exception:
                pass  # Non-blocking retrieval event persistence should not break chat  NON-NEGOTIABLE FEATURE

        return {
            'session_id': sid,
            'answer': answer,
            'citations': citations,
            'tool_traces': traces,
            'retrieval_event': retrieval_event,
            'trace_id': trace_id,
            'latency_ms': int((time.time() - started) * 1000),
        }

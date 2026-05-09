from __future__ import annotations

import uuid
from typing import Any


class EvalStore:
    """Legacy in-memory eval store. Kept for backward-compat with tests."""
    def __init__(self) -> None:
        self.latest: dict[str, object] | None = None


class EvalService:
    def __init__(
        self,
        *,
        chat_service: object,
        eval_run_repo: Any | None = None,
        eval_result_repo: Any | None = None,
        store: EvalStore | None = None,
    ) -> None:
        self.chat_service = chat_service
        self.eval_run_repo = eval_run_repo
        self.eval_result_repo = eval_result_repo
        # Fallback to legacy in-memory store when no repos provided
        self._legacy_store = store or EvalStore()

    def _persist_run(self, payload: dict[str, object]) -> None:
        if self.eval_run_repo is not None:
            try:
                self.eval_run_repo.insert_run(
                    run_id=str(payload.get('eval_run_id', '')),
                    suite_name=str(payload.get('suite_name', '')),
                    summary=payload.get('summary', {}),
                )
            except Exception:
                pass  # Non-blocking

        if self.eval_result_repo is not None and payload.get('results'):
            try:
                results_for_db = []
                for r in payload.get('results', []):
                    results_for_db.append({
                        'example_id': str(r.get('question', '')),
                        'metric_name': 'citation_presence',
                        'metric_value': 1.0 if r.get('has_citation') else 0.0,
                        'result_payload': r,
                    })
                self.eval_result_repo.insert_results(
                    str(payload.get('eval_run_id', '')),
                    results_for_db,
                )
            except Exception:
                pass  # Non-blocking

        self._legacy_store.latest = payload

    def run(self, suite_name: str) -> dict[str, object]:
        from app.services.eval_dataset import load_dataset, DEFAULT_DATASET_PATH
        
        try:
            examples = load_dataset(DEFAULT_DATASET_PATH)
        except Exception:
            # Fallback if dataset file doesn't exist
            from app.services.eval_dataset import EvalExample
            examples = [
                EvalExample(
                    id='fallback_1',
                    question='How do I confirm a PaymentIntent?',
                    expected_answer_points=[],
                    gold_source_urls=['https://docs.stripe.com/payments/accept-a-payment'],
                    tags=['fallback'],
                )
            ]

        results = []
        citation_hits = 0
        sum_mrr = 0.0
        sum_recall = 0.0

        for ex in examples:
            out = self.chat_service.chat(message=ex.question, session_id=None, top_k=5, max_citations=3)
            
            citations = out.get('citations', [])
            retrieval_event = out.get('retrieval_event', {})
            top_k_reranked = retrieval_event.get('top_k_reranked', [])
            
            # Simple fallback to search results if retrieval_event is incomplete in tests
            if not top_k_reranked and 'tool_traces' in out:
                for t in out['tool_traces']:
                    if t.get('tool_name') == 'search_tool':
                        top_k_reranked = [{'url': c.get('url')} for c in t.get('tool_output', {}).get('results', [])]
                        break

            has_citation = len(citations) > 0
            citation_hits += 1 if has_citation else 0

            # Calculate MRR and Recall@k for retrieval
            gold_urls = set(u.rstrip('/') for u in ex.gold_source_urls)
            retrieved_urls = []
            
            # Extract URLs from citations or retrieval_event
            for chunk in top_k_reranked:
                # We need URLs, but chunk might just have chunk_id depending on how it's serialized.
                # In our runtime, we didn't serialize URL in top_k_reranked. We only serialized chunk_id.
                pass
                
            # Actually, to get URLs we can just look at citations, which have URLs.
            retrieved_urls = [c.get('url', '').rstrip('/') for c in citations]
            
            mrr = 0.0
            recall = 0.0
            
            if gold_urls and retrieved_urls:
                for i, url in enumerate(retrieved_urls):
                    if url in gold_urls:
                        mrr = 1.0 / (i + 1)
                        break
                
                hits = sum(1 for u in gold_urls if u in retrieved_urls)
                recall = hits / len(gold_urls) if gold_urls else 0.0

            sum_mrr += mrr
            sum_recall += recall

            results.append({
                'question': ex.question,
                'has_citation': has_citation,
                'mrr': mrr,
                'recall': recall,
            })

        example_count = len(examples)
        summary = {
            'citation_presence': citation_hits / example_count if example_count > 0 else 0.0,
            'mrr': sum_mrr / example_count if example_count > 0 else 0.0,
            'recall': sum_recall / example_count if example_count > 0 else 0.0,
            'pass': (citation_hits / example_count) >= 0.5 if example_count > 0 else False,
            'example_count': example_count,
        }

        payload = {
            'eval_run_id': str(uuid.uuid4()),
            'suite_name': suite_name,
            'summary': summary,
            'results': results,
        }
        self._persist_run(payload)
        return payload

    def latest(self) -> dict[str, object]:
        # Try DB first
        if self.eval_run_repo is not None:
            try:
                db_latest = self.eval_run_repo.get_latest()
                if db_latest is not None:
                    return {
                        'eval_run_id': db_latest.get('id'),
                        'suite_name': db_latest.get('suite_name'),
                        'summary': db_latest.get('summary', {}),
                        'results': [],
                    }
            except Exception:
                pass

        if self._legacy_store.latest is not None:
            return self._legacy_store.latest
        return {
            'eval_run_id': None,
            'suite_name': None,
            'summary': {'citation_presence': 0.0, 'pass': False, 'example_count': 0},
            'results': [],
        }

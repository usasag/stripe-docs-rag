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
                # If it already exists, this might fail, so we should do an upsert or check
                existing = self.eval_run_repo.get_run(str(payload.get('eval_run_id', '')))
                if not existing:
                    self.eval_run_repo.insert_run(
                        run_id=str(payload.get('eval_run_id', '')),
                        suite_name=str(payload.get('suite_name', '')),
                        summary=payload.get('summary', {}),
                    )
                else:
                    # Update summary if the repo supports it, for now we just try insert
                    pass
            except Exception:
                pass

        if self.eval_result_repo is not None and payload.get('results'):
            try:
                results_for_db = []
                for r in payload.get('results', []):
                    results_for_db.append({
                        'example_id': str(r.get('question', '')),
                        'metric_name': 'faithfulness',
                        'metric_value': r.get('llm_scores', {}).get('faithfulness', 0),
                        'result_payload': r,
                    })
                self.eval_result_repo.insert_results(
                    str(payload.get('eval_run_id', '')),
                    results_for_db,
                )
            except Exception:
                pass

        self._legacy_store.latest = payload

    def start_eval_run(self, suite_name: str, background_tasks: Any) -> str:
        """Kicks off an async eval run and returns the run_id."""
        run_id = str(uuid.uuid4())
        
        # Initialize the run in the DB immediately with 'running' status
        initial_payload = {
            'eval_run_id': run_id,
            'suite_name': suite_name,
            'summary': {'status': 'running'},
            'results': []
        }
        self._persist_run(initial_payload)
        
        # Schedule the background task
        background_tasks.add_task(self._run_evals_async, run_id, suite_name)
        return run_id

    async def _run_evals_async(self, run_id: str, suite_name: str) -> None:
        import asyncio
        from app.services.eval_dataset import load_dataset, DEFAULT_DATASET_PATH
        from app.evals.llm_judge import LiteLLMJudge
        
        judge = LiteLLMJudge()
        
        try:
            examples = load_dataset(DEFAULT_DATASET_PATH)
        except Exception:
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
        
        # LLM Metric sums
        sum_faithfulness = 0
        sum_relevance = 0
        sum_accuracy = 0
        sum_citation_precision = 0

        for ex in examples:
            out = self.chat_service.chat(message=ex.question, session_id=None, top_k=5, max_citations=3)
            
            answer = str(out.get('answer', ''))
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
            
            # Formulate context for the LLM Judge
            context_texts = [f"URL: {c.get('url')}\nContent: {c.get('content', '')}" for c in citations]
            context_block = "\n\n".join(context_texts)
            
            # Call LLM Judge
            # We use an asyncio wrapper or run it in threadpool since litellm can be sync
            llm_scores = await asyncio.to_thread(
                judge.evaluate,
                question=ex.question,
                answer=answer,
                context=context_block,
                expected_points=ex.expected_answer_points
            )
            
            sum_faithfulness += llm_scores.get('faithfulness', 0)
            sum_relevance += llm_scores.get('relevance', 0)
            sum_accuracy += llm_scores.get('accuracy', 0)
            sum_citation_precision += llm_scores.get('citation_precision', 0)

            results.append({
                'question': ex.question,
                'has_citation': has_citation,
                'mrr': mrr,
                'recall': recall,
                'llm_scores': llm_scores
            })

        example_count = len(examples)
        summary = {
            'status': 'completed',
            'citation_presence': citation_hits / example_count if example_count > 0 else 0.0,
            'mrr': sum_mrr / example_count if example_count > 0 else 0.0,
            'recall': sum_recall / example_count if example_count > 0 else 0.0,
            'avg_faithfulness': sum_faithfulness / example_count if example_count > 0 else 0.0,
            'avg_relevance': sum_relevance / example_count if example_count > 0 else 0.0,
            'avg_accuracy': sum_accuracy / example_count if example_count > 0 else 0.0,
            'avg_citation_precision': sum_citation_precision / example_count if example_count > 0 else 0.0,
            'pass': (citation_hits / example_count) >= 0.5 if example_count > 0 else False,
            'example_count': example_count,
        }

        payload = {
            'eval_run_id': run_id,
            'suite_name': suite_name,
            'summary': summary,
            'results': results,
        }
        self._persist_run(payload)

    def latest(self) -> dict[str, object]:
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
            'summary': {'status': 'none'},
            'results': [],
        }

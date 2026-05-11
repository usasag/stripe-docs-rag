import json
import logging
from pydantic import BaseModel, Field
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class JudgeScores(BaseModel):
    faithfulness: int = Field(..., ge=1, le=5, description="1-5 score indicating if the answer is fully grounded in the provided context without hallucinations (5 being perfectly grounded).")
    relevance: int = Field(..., ge=1, le=5, description="1-5 score indicating if the answer directly addresses the user's question (5 being directly answering).")
    accuracy: int = Field(..., ge=1, le=5, description="1-5 score indicating if the answer covers the expected_answer_points (5 being all points covered).")
    citation_precision: int = Field(..., ge=1, le=5, description="1-5 score indicating if citations match and correctly support the claims made (5 being accurate and supportive).")
    rationale: str = Field(..., description="A short explanation (4 phrases max) justifying the scores.")

class LiteLLMJudge:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model = self.settings.llm_judge_model
        # Use litellm if api key is provided, else we fallback
        if self.settings.llm_api_key:
            import os
            os.environ["LITELLM_API_KEY"] = self.settings.llm_api_key
            # If using GitHub models or specific ones, we might need specific keys, 
            # but litellm typically routes OPENAI_API_KEY, ANTHROPIC_API_KEY, or we can just pass api_key directly.
        
    def evaluate(self, question: str, answer: str, context: str, expected_points: list[str]) -> dict:
        """Evaluates a RAG turn and returns a dictionary of 1-5 scalar scores."""
        
        if not self.settings.llm_api_key:
            logger.warning("LLM Judge is disabled (no llm_api_key). Returning default scores.")
            return {
                "faithfulness": 3,
                "relevance": 3,
                "accuracy": 3,
                "citation_precision": 3,
                "rationale": "Judge disabled due to missing API key."
            }

        try:
            from litellm import completion
            
            prompt = f"""You are an expert evaluator grading a RAG (Retrieval-Augmented Generation) agent.
            
Evaluate the following interaction based on 4 metrics, assigning a score from 1 to 5 for each:
1. Faithfulness: Is the generated answer grounded entirely in the provided context? (1 = full of hallucinations, 5 = perfectly grounded)
2. Relevance: Does the generated answer address the question? (1 = off-topic, 5 = directly answers)
3. Accuracy: Does the generated answer include the Expected Points? (1 = misses all points, 5 = covers all points)
4. Citation Precision: Are citations used appropriately? (1 = no/wrong citations, 5 = accurate, helpful citations)

Question: {question}

Expected Points to Cover:
{chr(10).join(f'- {p}' for p in expected_points)}

Retrieved Context:
{context}

Generated Answer:
{answer}
"""
            # Call litellm using the configured model and the Pydantic schema for structured output
            # litellm supports response_format for OpenAI/Anthropic/etc.
            # However, for maximum compatibility across different models (like HuggingFace),
            # we ask for JSON directly or use OpenAI's structured outputs via litellm if supported.
            # To be safe across providers, we prompt for JSON and parse.
            
            messages = [
                {"role": "system", "content": "You must output your evaluation strictly as a JSON object matching the requested schema. Output ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            schema = JudgeScores.model_json_schema()
            messages[0]["content"] += f"\n\nJSON Schema:\n{json.dumps(schema)}"
            
            fallback_models = [
                "huggingface/meta-llama/Meta-Llama-3-70B-Instruct",
                "huggingface/mistralai/Mixtral-8x7B-Instruct-v0.1"
            ]
            
            response = completion(
                model=self.model,
                fallbacks=fallback_models,
                messages=messages,
                api_key=self.settings.llm_api_key,
                response_format={"type": "json_object"},
                max_tokens=1024,
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            # Parse the JSON
            parsed = json.loads(content)
            # Validate via Pydantic to ensure types and ranges
            validated = JudgeScores(**parsed)
            return validated.model_dump()
            
        except Exception as e:
            logger.exception(f"Failed to run LiteLLMJudge evaluation: {e}")
            return {
                "faithfulness": 0,
                "relevance": 0,
                "accuracy": 0,
                "citation_precision": 0,
                "rationale": f"Evaluation failed: {str(e)}"
            }

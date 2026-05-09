"""Eval dataset loader and schema validation.

Loads QA golden datasets from JSONL files for use by the eval service.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalExample:
    """A single evaluation example."""
    id: str
    question: str
    expected_answer_points: list[str] = field(default_factory=list)
    gold_source_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def load_dataset(path: str) -> list[EvalExample]:
    """Load eval examples from a JSONL file.

    Each line should be a JSON object with at least ``id`` and ``question``.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f'Eval dataset not found: {path}')

    examples: list[EvalExample] = []
    with open(path, encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'Invalid JSON on line {line_num}: {exc}') from exc

            if 'id' not in obj or 'question' not in obj:
                raise ValueError(f'Line {line_num} missing required fields (id, question)')

            examples.append(
                EvalExample(
                    id=str(obj['id']),
                    question=str(obj['question']),
                    expected_answer_points=obj.get('expected_answer_points', []),
                    gold_source_urls=obj.get('gold_source_urls', []),
                    tags=obj.get('tags', []),
                )
            )

    return examples


# Default dataset path
DEFAULT_DATASET_PATH = os.path.join(os.path.dirname(__file__), '..', 'evals', 'datasets', 'qa_goldens.jsonl')

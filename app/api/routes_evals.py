from __future__ import annotations

from fastapi import APIRouter, Depends, BackgroundTasks

from app.api.deps import eval_service_dep
from app.domain.schemas import EvalLatestResponse, EvalRunRequest, EvalRunResponse

router = APIRouter(tags=['evals'])


@router.post('/evals/run', response_model=EvalRunResponse)
def run_evals(
    payload: EvalRunRequest, 
    background_tasks: BackgroundTasks, 
    service=Depends(eval_service_dep)
) -> EvalRunResponse:
    run_id = service.start_eval_run(payload.suite_name, background_tasks)
    return EvalRunResponse(eval_run_id=run_id, suite_name=payload.suite_name, summary={"status": "running"})


@router.get('/evals/latest', response_model=EvalLatestResponse)
def latest_evals(service=Depends(eval_service_dep)) -> EvalLatestResponse:
    out = service.latest()
    return EvalLatestResponse(eval_run_id=out.get('eval_run_id'), suite_name=out.get('suite_name'), summary=out.get('summary', {}))

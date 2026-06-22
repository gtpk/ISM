from __future__ import annotations

from dataclasses import asdict, dataclass

from ism.config import AppConfig


@dataclass(frozen=True)
class ExecutionPlan:
    stage: str
    documents: int
    questions: int
    conditions: int
    budgets: int
    seeds: int
    compression_calls: int
    reasoning_calls: int
    nominal_calls: int
    worst_case_calls: int
    max_new_tokens_per_call: int
    max_gpu_hours: float

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def build_execution_plan(config: AppConfig) -> ExecutionPlan:
    documents = config.dataset.max_documents
    questions = documents * config.dataset.questions_per_document
    conditions = len(config.conditions)
    budgets = config.execution_budget.max_budgets
    seeds = config.execution_budget.max_seeds

    compression_families = {
        family
        for condition in config.conditions
        if (family := _compression_family(condition)) is not None
    }
    compression_calls = documents * len(compression_families) * budgets * seeds
    reasoning_calls = questions * conditions * budgets * seeds
    nominal_calls = compression_calls + reasoning_calls
    retry_multiplier = config.execution_budget.max_generation_attempts

    return ExecutionPlan(
        stage=config.execution_budget.stage.value,
        documents=documents,
        questions=questions,
        conditions=conditions,
        budgets=budgets,
        seeds=seeds,
        compression_calls=compression_calls,
        reasoning_calls=reasoning_calls,
        nominal_calls=nominal_calls,
        worst_case_calls=nominal_calls * retry_multiplier,
        max_new_tokens_per_call=config.execution_budget.max_new_tokens,
        max_gpu_hours=config.execution_budget.max_gpu_hours,
    )


def _compression_family(condition: str) -> str | None:
    if condition == "full_context":
        return None
    if condition in {
        "full_symbol_dict",
        "symbol_only",
        "corrupted_dict",
        "random_symbol",
        "unseen_swap_dict",
        "unseen_swap_no_dict",
    }:
        return "ism"
    if condition == "model_summary":
        return "model_summary"
    if condition == "llmlingua_2":
        return "llmlingua_2"
    if condition == "keyword_extract":
        return "keyword_extract"
    raise ValueError(f"unsupported condition: {condition}")

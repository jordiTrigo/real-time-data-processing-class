"""Offline, deterministic incident-agent evaluation fixtures."""

__all__ = ["EvaluationResult", "run_all"]


def __getattr__(name: str):
    """Keep ``python -m evals.runner`` free of eager-import warnings."""

    if name in __all__:
        from .runner import EvaluationResult, run_all

        return {"EvaluationResult": EvaluationResult, "run_all": run_all}[name]
    raise AttributeError(name)

"""Typed models for the Horizon surface.

Load-bearing responses — suite runs, prompt-optimization results, routing
policies, grades — are pydantic models so callers use attribute access
(``run.rate``, ``opt.best_label``) rather than dict indexing. ``extra="allow"``
keeps them forward-compatible: a new server field is preserved, never fatal.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

JsonList = list[dict[str, Any]]


class _H(BaseModel):
    """Base for Horizon responses — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow")


class SuiteRun(_H):
    """The scored result of running a suite (``suites.run``)."""

    run_at: str | None = None
    passed: int = 0
    total: int = 0
    rate: float = 0.0
    eval: bool = False
    mean_reward: float | None = None
    mean_latency_ms: float | None = None
    tool_errors: int = 0
    tokens: int = 0
    policy: str | None = None
    results: JsonList = Field(default_factory=list)


class PromptTrial(_H):
    """One candidate evaluated during a prompt-optimization run."""

    label: str = ""
    template: str = ""
    rate: float = 0.0
    mean_reward: float = 0.0
    score: float = 0.0
    passed: int = 0
    total: int = 0
    tool_errors: int = 0
    tokens: int = 0
    mean_latency_ms: float | None = None


class PromptOptimization(_H):
    """The result of optimizing a prompt against a suite (``prompts.optimize``)."""

    prompt_id: str = ""
    suite_id: str = ""
    scope: str | None = None
    metric: str = "rate"
    deployed: bool = False
    best_label: str | None = None
    best_rate: float | None = None
    best_reward: float | None = None
    trials: list[PromptTrial] = Field(default_factory=list)


class RoutingPolicies(_H):
    """The routing policies and the space they decide over (``routing.policies``)."""

    active: str | None = None
    policies: list[Any] = Field(default_factory=list)
    action_space: dict[str, Any] | None = None
    state_space: list[Any] | None = None


class Grade(_H):
    """A recorded grade (``grades.grade``)."""

    ok: bool = False
    session_id: str | None = None
    turn: int = 0
    goal_met: bool = False
    score: float | None = None
    grader: str = ""
    live_applied: bool = False


class JudgeVerdict(_H):
    """An LLM-as-judge verdict (``grades.judge``)."""

    score: float | None = None
    goal_met: bool = False
    by: str = ""
    reason: str = ""
    live_applied: bool = False


class TrainerRun(_H):
    """The result of a synchronous trainer run (``trainers.train``)."""

    ok: bool = False
    kind: str = ""
    dataset_id: str | None = None
    samples: int = 0
    applied: int = 0
    saved: bool = False
    policy_delta: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None
    status: str = ""
    duration_ms: int | None = None

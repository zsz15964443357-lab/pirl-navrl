"""Policy protocol used by TASK_03 diagnostic rollouts."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from pirl_navrl.scenarios.core import ScenarioConfig


class PolicyLike(Protocol):
    policy_id: str

    def reset(self, scenario: ScenarioConfig) -> None:
        ...

    def act(self, observation: Mapping[str, Any]) -> Any:
        ...

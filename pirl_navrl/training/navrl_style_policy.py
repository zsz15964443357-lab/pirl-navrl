"""NavRL-style SB3 feature extractor for TASK_06 diagnostics."""

from __future__ import annotations

import gymnasium as gym
import torch
from torch import nn

try:  # pragma: no cover - exercised only when SB3 is installed.
    from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
except Exception:  # pragma: no cover
    BaseFeaturesExtractor = object  # type: ignore[misc,assignment]


class NavRLStyleFeatureExtractor(BaseFeaturesExtractor):
    """Approximate NavRL's lidar/state/dynamic-obstacle extractor in SB3.

    The original NavRL policy uses separate CNN and dynamic-obstacle branches,
    then concatenates those features with the robot state. This extractor keeps
    that structure while staying compatible with SB3 `MultiInputPolicy`.
    """

    def __init__(self, observation_space: gym.spaces.Dict, features_dim: int = 256) -> None:
        super().__init__(observation_space, features_dim)
        lidar_shape = observation_space["lidar"].shape
        if lidar_shape != (1, 36, 4):
            raise ValueError(f"expected NavRL-style lidar shape (1, 36, 4), got {lidar_shape}")
        self.lidar_cnn = nn.Sequential(
            nn.Conv2d(1, 4, kernel_size=(5, 3), padding=(2, 1)),
            nn.ELU(),
            nn.Conv2d(4, 16, kernel_size=(5, 3), stride=(2, 1), padding=(2, 1)),
            nn.ELU(),
            nn.Conv2d(16, 16, kernel_size=(5, 3), stride=(2, 2), padding=(2, 1)),
            nn.ELU(),
            nn.Flatten(),
        )
        with torch.no_grad():
            sample = torch.zeros(1, *lidar_shape)
            lidar_flattened = int(self.lidar_cnn(sample).shape[1])
        self.lidar_head = nn.Sequential(
            nn.Linear(lidar_flattened, 128),
            nn.LayerNorm(128),
        )
        self.dynamic_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(50, 128),
            nn.LeakyReLU(),
            nn.LayerNorm(128),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.LayerNorm(64),
        )
        self.fusion = nn.Sequential(
            nn.Linear(128 + 64 + 8 + 3, features_dim),
            nn.LeakyReLU(),
            nn.LayerNorm(features_dim),
            nn.Linear(features_dim, features_dim),
            nn.LeakyReLU(),
            nn.LayerNorm(features_dim),
        )

    def forward(self, observations: dict[str, torch.Tensor]) -> torch.Tensor:
        lidar_feature = self.lidar_head(self.lidar_cnn(observations["lidar"].float()))
        dynamic_feature = self.dynamic_head(observations["dynamic_obstacle"].float())
        state = observations["state"].float()
        direction = observations["direction"].float().flatten(start_dim=1)
        return self.fusion(torch.cat([lidar_feature, state, direction, dynamic_feature], dim=1))

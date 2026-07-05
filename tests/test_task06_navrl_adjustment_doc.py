from pathlib import Path


def test_task06_navrl_adjustment_doc_has_concrete_references() -> None:
    text = Path("docs/navrl_guided_training_adjustments_task06.md").read_text(encoding="utf-8")

    for phrase in [
        "external/NavRL/quick-demos/env.py",
        "external/NavRL/isaac-training/training/scripts/env.py",
        "static_obstacle_easy",
        "dynamic_crossing_easy",
        "latent_dynamic_easy",
        "feature_scaling.py",
        "reward_profiles.py",
        "case selector",
    ]:
        assert phrase in text

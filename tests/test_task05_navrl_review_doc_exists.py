from pathlib import Path


def test_task05_navrl_review_doc_exists_and_covers_required_topics() -> None:
    path = Path("docs/navrl_code_review_for_task05.md")
    text = path.read_text(encoding="utf-8")

    for phrase in [
        "Repository Structure",
        "Scenario, Obstacle, and Start/Goal",
        "Observation, Action, and Reward",
        "Training, Runner, Logging, and Checkpoint",
        "Attribution and License",
        "TASK_05",
    ]:
        assert phrase in text


def test_task05_training_readiness_doc_exists() -> None:
    text = Path("docs/task05_training_readiness_review.md").read_text(encoding="utf-8")

    assert "terminated = success or collision" in text
    assert "truncated = timeout" in text
    assert "outputs/" in text

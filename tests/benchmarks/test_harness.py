from consignai.evaluation.benchmark import evaluate


def test_reproducible_evaluation_outputs(tmp_path):
    result = evaluate(tmp_path, seed=42, contractors=5, skus=15, days=90, slots=2)
    assert result["reconciliation"]["accuracy"] == 1
    assert result["redistribution"]["valid"]
    assert result["forecast"]["windows"] > 0
    assert result["detection"]["recall"] == 1
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "metrics.csv").exists()
    assert (tmp_path / "summary.md").exists()

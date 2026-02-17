import pandas as pd


def test_optimize_matching_selects_best_matcher():
    from PyDI.pipeline.optimization import optimize_matching

    df_left = pd.DataFrame(
        [
            {"id": "l1", "title": "Alpha"},
            {"id": "l2", "title": "Beta"},
            {"id": "l3", "title": "Gamma"},
        ]
    )
    df_right = pd.DataFrame(
        [
            {"id": "r1", "title": "Alpha"},
            {"id": "r2", "title": "Beta"},
            {"id": "r3", "title": "Gamma"},
        ]
    )

    # Validation set (2 positives + 4 negatives)
    validation_set = pd.DataFrame(
        [
            {"id1": "l1", "id2": "r1", "label": "TRUE"},
            {"id1": "l2", "id2": "r2", "label": "TRUE"},
            {"id1": "l1", "id2": "r2", "label": "FALSE"},
            {"id1": "l1", "id2": "r3", "label": "FALSE"},
            {"id1": "l2", "id2": "r1", "label": "FALSE"},
            {"id1": "l2", "id2": "r3", "label": "FALSE"},
        ]
    )

    # Training set (1 positive + 2 negatives), no pair overlap with validation
    training_set = pd.DataFrame(
        [
            {"id1": "l3", "id2": "r3", "label": "TRUE"},
            {"id1": "l3", "id2": "r1", "label": "FALSE"},
            {"id1": "l3", "id2": "r2", "label": "FALSE"},
        ]
    )

    out = optimize_matching(
        df_left=df_left,
        df_right=df_right,
        validation_set=validation_set,
        id_column="id",
        matching_columns=["title"],
        thresholds=[0.0, 0.5, 0.8, 0.9, 1.0],
        include_rule_based=True,
        include_ml_based=True,
        training_set=training_set,
    )

    assert out["best"] is not None
    assert not out["all_results"].empty
    assert out["best"]["f1"] >= 0.9


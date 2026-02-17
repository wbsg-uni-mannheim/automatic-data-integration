import pandas as pd


def test_run_data_fusion_auto_strategy():
    from PyDI.pipeline import FusionConfig, run_data_fusion

    df_a = pd.DataFrame(
        {
            "id": ["a-0"],
            "title": ["My Movie"],
            "date": ["2010-01-01"],
            "actors_actor_name": ["Alice,Bob"],
            "rating": [8.0],
            "oscar": [True],
        }
    )
    df_b = pd.DataFrame(
        {
            "id": ["b-0"],
            "title": ["My Movie (Extended)"],
            "date": ["2010-01-01"],
            "actors_actor_name": [["Alice", "Bob", "Carol"]],
            "rating": [9.0],
            "oscar": [True],
        }
    )

    corr = pd.DataFrame({"id1": ["a-0"], "id2": ["b-0"], "score": [0.9]})

    fused, strategy, _ = run_data_fusion(
        {"A": df_a, "B": df_b},
        correspondences=corr,
        config=FusionConfig(id_column="id", include_singletons=True, debug=False),
        output_dir=None,
    )

    assert strategy is not None
    assert len(fused) == 1
    row = fused.iloc[0]

    # title -> longest_string
    assert row["title"] == "My Movie (Extended)"
    # list-ish actors -> union
    assert set(row["actors_actor_name"]) == {"Alice", "Bob", "Carol"}
    # numeric -> median
    assert float(row["rating"]) == 8.5
    # boolean -> voting
    assert bool(row["oscar"]) is True
    # fusion metadata
    assert "_fusion_sources" in fused.columns
    assert "_fusion_confidence" in fused.columns


def test_run_data_fusion_llm_strategy_offline():
    from PyDI.pipeline import FusionConfig, run_data_fusion
    import json

    class _Resp:
        def __init__(self, content: str):
            self.content = content

    class DummyChatModel:
        def invoke(self, messages):
            payload = {
                "main_entity": "movie",
                "attribute_rules": {
                    "title": {"resolver": "longest_string", "kwargs": {}},
                    "actors_actor_name": {"resolver": "union", "kwargs": {"separator": ","}},
                    "rating": {"resolver": "median", "kwargs": {}},
                    "date": {"resolver": "most_recent", "kwargs": {}},
                    "oscar": {"resolver": "voting", "kwargs": {}},
                },
            }
            return _Resp(json.dumps(payload))

    df_a = pd.DataFrame(
        {
            "id": ["a-0"],
            "title": ["My Movie"],
            "date": ["2010-01-01"],
            "actors_actor_name": ["Alice,Bob"],
            "rating": [8.0],
            "oscar": [True],
        }
    )
    df_b = pd.DataFrame(
        {
            "id": ["b-0"],
            "title": ["My Movie (Extended)"],
            "date": ["2011-01-01"],
            "actors_actor_name": ["Bob,Carol"],
            "rating": [10.0],
            "oscar": [True],
        }
    )
    corr = pd.DataFrame({"id1": ["a-0"], "id2": ["b-0"], "score": [0.9]})

    fused, _, _ = run_data_fusion(
        {"A": df_a, "B": df_b},
        correspondences=corr,
        config=FusionConfig(id_column="id", include_singletons=True, debug=False, use_llm=True, force_replan=True),
        chat_model=DummyChatModel(),
        output_dir=None,
    )

    row = fused.iloc[0]
    assert row["title"] == "My Movie (Extended)"
    assert set(row["actors_actor_name"]) == {"Alice", "Bob", "Carol"}
    assert float(row["rating"]) == 9.0

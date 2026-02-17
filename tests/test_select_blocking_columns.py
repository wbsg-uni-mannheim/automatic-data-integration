import pandas as pd


class _DummyResponse:
    def __init__(self, content: str):
        self.content = content


class _DummyChatModel:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, _messages):
        return _DummyResponse(self._content)


def test_select_blocking_columns_allows_identifier_columns():
    from PyDI.pipeline.entity_resolution import select_blocking_columns

    df_left = pd.DataFrame(
        [
            {"id": "l1", "isbn": "978-0-00-000000-1", "title": "Alpha", "actors_actor_name": "A, B"},
            {"id": "l2", "isbn": None, "title": "Beta", "actors_actor_name": "C, D"},
        ]
    )
    df_right = pd.DataFrame(
        [
            {"id": "r1", "isbn": "978-0-00-000000-1", "title": "Alpha", "actors_actor_name": "A, B"},
            {"id": "r2", "isbn": None, "title": "Beta", "actors_actor_name": "C, D"},
        ]
    )

    chat = _DummyChatModel('["isbn"]')
    cols = select_blocking_columns(df_left, df_right, chat, id_column="id")
    assert cols == ["isbn"]


def test_select_blocking_columns_heuristic_avoids_actor_list_when_llm_fails():
    from PyDI.pipeline.entity_resolution import select_blocking_columns

    df_left = pd.DataFrame(
        [
            {"id": "l1", "title": "Fight Club", "actors_actor_name": "Brad Pitt, Edward Norton"},
            {"id": "l2", "title": "Heat", "actors_actor_name": "Al Pacino, Robert De Niro"},
        ]
    )
    df_right = pd.DataFrame(
        [
            {"id": "r1", "title": "Fight Club", "actors_actor_name": "Brad Pitt, Edward Norton"},
            {"id": "r2", "title": "Heat", "actors_actor_name": "Al Pacino, Robert De Niro"},
        ]
    )

    # Trigger fallback: invalid JSON
    chat = _DummyChatModel("not json")
    cols = select_blocking_columns(df_left, df_right, chat, id_column="id")
    assert cols[0] == "title"


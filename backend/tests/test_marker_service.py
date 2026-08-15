from app.services.marker_service import extract_markers


def test_extract_markers_follows_content_order_and_limits_to_three() -> None:
    markers = extract_markers("毕业后第一次去旅行，回来后完成了作品。")

    assert [(marker.type, marker.keyword) for marker in markers] == [
        ("achievement", "毕业"),
        ("growth", "第一次"),
        ("place", "旅行"),
    ]


def test_extract_markers_returns_each_dictionary_keyword_once() -> None:
    markers = extract_markers("今天完成一件事，明天还要继续完成另一件事。")

    assert [marker.keyword for marker in markers] == ["完成"]


def test_extract_markers_does_not_force_unmatched_tags() -> None:
    assert extract_markers("今天喝了一杯咖啡。") == []

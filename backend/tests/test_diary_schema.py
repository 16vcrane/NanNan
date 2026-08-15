import uuid

import pytest
from pydantic import ValidationError

from app.schemas.diary import DiaryCreateRequest


def test_diary_content_is_preserved() -> None:
    payload = DiaryCreateRequest(
        content="  今天很好。\n",
        energyScore=65,
        moodLabel="愉悦",
        imageIds=[],
    )

    assert payload.content == "  今天很好。\n"
    assert payload.energy_score == 65


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_blank_diary_content_is_rejected(content: str) -> None:
    with pytest.raises(ValidationError):
        DiaryCreateRequest(content=content)


@pytest.mark.parametrize("energy_score", [-1, 101])
def test_invalid_energy_score_is_rejected(energy_score: int) -> None:
    with pytest.raises(ValidationError):
        DiaryCreateRequest(content="有效内容", energyScore=energy_score)


def test_up_to_three_unique_images_are_allowed() -> None:
    image_ids = [uuid.uuid4() for _ in range(3)]

    payload = DiaryCreateRequest(content="有效内容", imageIds=image_ids)

    assert payload.image_ids == image_ids


def test_more_than_three_images_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DiaryCreateRequest(
            content="有效内容",
            imageIds=[uuid.uuid4() for _ in range(4)],
        )


def test_duplicate_images_are_rejected() -> None:
    image_id = uuid.uuid4()

    with pytest.raises(ValidationError):
        DiaryCreateRequest(content="有效内容", imageIds=[image_id, image_id])

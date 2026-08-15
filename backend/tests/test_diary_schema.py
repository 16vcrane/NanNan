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


def test_images_are_not_silently_discarded_before_phase_four() -> None:
    with pytest.raises(ValidationError):
        DiaryCreateRequest(content="有效内容", imageIds=[uuid.uuid4()])

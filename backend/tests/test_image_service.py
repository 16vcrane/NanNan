import io

import pytest
from PIL import Image

from app.core.storage import LocalStorageBackend, StorageError
from app.services.image_service import (
    MAX_IMAGE_SIDE,
    MAX_UPLOAD_BYTES,
    ImageValidationError,
    normalize_image,
)


def make_image_bytes(
    *,
    image_format: str = "PNG",
    size: tuple[int, int] = (80, 60),
    mode: str = "RGBA",
) -> bytes:
    image = Image.new(mode, size, (220, 120, 80, 180))
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def test_normalize_image_converts_and_resizes() -> None:
    normalized = normalize_image(make_image_bytes(size=(3000, 1200)))

    with Image.open(io.BytesIO(normalized)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert max(image.size) == MAX_IMAGE_SIDE


def test_normalize_image_rejects_non_image_content() -> None:
    with pytest.raises(ImageValidationError):
        normalize_image(b"not-an-image")


def test_normalize_image_rejects_oversized_upload() -> None:
    with pytest.raises(ImageValidationError, match="10MB"):
        normalize_image(b"x" * (MAX_UPLOAD_BYTES + 1))


@pytest.mark.asyncio
async def test_local_storage_round_trip_and_key_validation(tmp_path) -> None:
    storage = LocalStorageBackend(str(tmp_path))

    await storage.write("users/user-1/image.jpg", b"image", "image/jpeg")
    assert await storage.read("users/user-1/image.jpg") == b"image"

    await storage.delete("users/user-1/image.jpg")
    with pytest.raises(StorageError):
        await storage.read("users/user-1/image.jpg")
    with pytest.raises(StorageError):
        storage.path_for_key("../outside.jpg")

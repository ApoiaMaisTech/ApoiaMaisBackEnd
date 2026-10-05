import os
from pathlib import Path

import pytest

from app.infrastructure.storage import InvalidStorageKey, LocalObjectStorage, S3ObjectStorage

KEY = "ai-images/" + "ab" * 16 + ".png"


@pytest.mark.asyncio
async def test_local_le_arquivo_e_devolve_none_se_nao_existe(tmp_path: Path):
    (tmp_path / "ai-images").mkdir()
    (tmp_path / KEY).write_bytes(b"png")
    storage = LocalObjectStorage(str(tmp_path))

    assert await storage.get(KEY) == b"png"
    assert await storage.get("ai-images/" + "cd" * 16 + ".png") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["../etc/passwd", "ai-images/../../etc/passwd", "/etc/passwd", "a/../../b"])
async def test_local_recusa_path_traversal(tmp_path: Path, key):
    with pytest.raises(InvalidStorageKey):
        await LocalObjectStorage(str(tmp_path)).get(key)


# S3_TEST_ENDPOINT=http://127.0.0.1:8333 S3_TEST_BUCKET=apoiamais-test (o teste Go grava o objeto)
@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("S3_TEST_ENDPOINT"), reason="S3_TEST_ENDPOINT não definido")
async def test_s3_le_objeto_gravado_pelo_go_worker():
    storage = S3ObjectStorage(
        bucket=os.environ["S3_TEST_BUCKET"],
        endpoint_url=os.environ["S3_TEST_ENDPOINT"],
        region="us-east-1",
        access_key=os.getenv("S3_TEST_ACCESS_KEY", "any"),
        secret_key=os.getenv("S3_TEST_SECRET_KEY", "any"),
    )

    assert await storage.get(KEY) == b"png-s3"
    assert await storage.get("ai-images/" + "cd" * 16 + ".png") is None

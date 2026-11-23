import pytest

from app.services.storage import LocalFileStorage, StorageError, safe_filename


@pytest.fixture()
def storage(tmp_path):
    s = LocalFileStorage(tmp_path / "uploads")
    s.ensure_layout()
    return s


def test_save_read_delete_roundtrip(storage):
    key = storage.save("hotels/test.jpg", b"data")
    assert storage.exists(key)
    assert storage.read(key) == b"data"
    storage.delete(key)
    assert not storage.exists(key)


@pytest.mark.parametrize(
    "bad_key",
    ["../secret.txt", "hotels/../../secret.txt", "/etc/passwd", "C:/Windows/win.ini", "..\\x.jpg", ""],
)
def test_rejects_path_traversal(storage, bad_key):
    with pytest.raises(StorageError):
        storage.save(bad_key, b"x")


def test_safe_filename_strips_user_supplied_name():
    name = safe_filename("../../My Hotel <photo>.JPG")
    assert name.endswith(".jpg")
    assert "/" not in name and ".." not in name and " " not in name
    assert safe_filename("a.jpg") != safe_filename("a.jpg")

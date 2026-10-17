"""Git archive input cannot escape the contract snapshot directory."""

import io
import tarfile
from types import SimpleNamespace

import pytest

from cepio import compatibility


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
        ("hardlink", tarfile.LNKTYPE),
        ("fifo", tarfile.FIFOTYPE),
    ],
)
def test_contract_archive_rejects_unsafe_members(tmp_path, monkeypatch, name, kind):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = "../../escape"
        archive.addfile(member)
    monkeypatch.setattr(
        compatibility.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=buffer.getvalue()),
    )
    with pytest.raises(ValueError, match="Unsafe path"):
        compatibility.snapshot_from_git_ref(tmp_path, "unused")


def test_contract_archive_extracts_regular_files_and_directories(tmp_path, monkeypatch):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        directory = tarfile.TarInfo("nested")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        member = tarfile.TarInfo("nested/contract.txt")
        member.size = 4
        archive.addfile(member, io.BytesIO(b"safe"))
    monkeypatch.setattr(
        compatibility.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=buffer.getvalue()),
    )

    class Catalogue:
        def snapshot(self, root):
            assert (root / "nested/contract.txt").read_bytes() == b"safe"
            return {"safe": True}

    monkeypatch.setattr(compatibility.ModuleCatalogue, "load", lambda *args: Catalogue())
    assert compatibility.snapshot_from_git_ref(tmp_path, "unused") == {"safe": True}

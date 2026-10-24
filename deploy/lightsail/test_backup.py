"""Archive safety tests; no AWS calls, databases or real user data."""

import hashlib
import io
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import override

from deploy.lightsail import backup


def add_file(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(data)
    archive.addfile(member, io.BytesIO(data))


class ArchiveSafetyTests(unittest.TestCase):
    temp: TemporaryDirectory[str] | None = None
    work: Path = Path()
    original_work: Path = Path()

    @override
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.original_work = backup.WORK
        backup.WORK = self.work

    @override
    def tearDown(self) -> None:
        backup.WORK = self.original_work
        if self.temp is not None:
            self.temp.cleanup()

    def make_archive(self, *, corrupted: bool = False, traversal: bool = False, missing: bool = False, wrong_release: bool = False) -> None:
        files = {"database.dump": b"disposable database bytes", "rows.fingerprints": b"row hashes", "objects/photo": b"image bytes"}
        if traversal:
            files["../outside"] = b"must never be extracted"
        checksums: dict[str, str] = {}
        for name, data in files.items():
            checksums[name] = hashlib.sha256(data).hexdigest()
        manifest = backup.Manifest(files=checksums, objects=[])
        if wrong_release:
            manifest.release = "unrelated-release"
        with tarfile.open(self.work / "backup.tar.gz", "w:gz") as archive:
            add_file(archive, "manifest.json", manifest.model_dump_json().encode())
            for name, data in files.items():
                if missing and name == "objects/photo":
                    continue
                add_file(archive, name, b"changed bytes" if corrupted and name == "objects/photo" else data)

    def test_valid_archive_checks_all_objects_and_extracts_only_restore_inputs(self) -> None:
        self.make_archive()
        backup.verify()
        self.assertEqual((self.work / "verified/database.dump").read_bytes(), b"disposable database bytes")
        self.assertEqual({path.name for path in (self.work / "verified").iterdir()}, {"database.dump", "rows.fingerprints"})

    def test_corrupted_media_fails_the_whole_backup(self) -> None:
        self.make_archive(corrupted=True)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            backup.verify()
        self.assertFalse((self.work / "verified").exists())

    def test_missing_media_fails_the_whole_backup(self) -> None:
        self.make_archive(missing=True)
        with self.assertRaisesRegex(ValueError, "Incomplete archive"):
            backup.verify()

    def test_parent_traversal_is_rejected_without_outside_writes(self) -> None:
        self.make_archive(traversal=True)
        with self.assertRaisesRegex(ValueError, "Unsafe archive path"):
            backup.verify()
        self.assertFalse((self.work.parent / "outside").exists())

    def test_symlink_members_are_never_followed(self) -> None:
        with tarfile.open(self.work / "backup.tar.gz", "w:gz") as archive:
            link = tarfile.TarInfo("database.dump")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            archive.addfile(link)
        with self.assertRaisesRegex(ValueError, "Unsupported archive members"):
            backup.verify()

    def test_duplicate_members_are_rejected(self) -> None:
        with tarfile.open(self.work / "backup.tar.gz", "w:gz") as archive:
            add_file(archive, "database.dump", b"one")
            add_file(archive, "database.dump", b"two")
        with self.assertRaisesRegex(ValueError, "Unsupported archive members"):
            backup.verify()

    def test_unrelated_release_is_rejected(self) -> None:
        self.make_archive(wrong_release=True)
        with self.assertRaisesRegex(ValueError, "Unsupported backup release"):
            backup.verify()


if __name__ == "__main__":
    _ = unittest.main()

"""Small corruption controls for the archive verifier, without kernel execution."""

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from verify import safe_name, verify_campaign


class ArchiveIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "workspace.tar.gz"
        content = b"closed protocol\n"
        with tarfile.open(self.archive, "w:gz") as archive:
            member = tarfile.TarInfo("workspace/program.md")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        self.manifest = {
            "schema": 1,
            "archive": {
                "path": self.archive.name,
                **self.entry(self.archive.read_bytes()),
            },
            "members": {"workspace/program.md": self.entry(content)},
            "records": {"report.md": self.entry(b"results-only\n")},
        }
        (self.root / "report.md").write_bytes(b"results-only\n")
        self.save_manifest()

    @staticmethod
    def entry(data):
        return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def save_manifest(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))

    def test_valid_fixture(self):
        self.assertEqual(verify_campaign(self.root)["members"], 1)

    def test_outer_corruption_rejected_before_decompression(self):
        data = bytearray(self.archive.read_bytes())
        data[0] ^= 1
        self.archive.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch: workspace.tar.gz"):
            verify_campaign(self.root)

    def test_member_hash_checked_separately(self):
        self.manifest["members"]["workspace/program.md"]["sha256"] = "0" * 64
        self.save_manifest()
        with self.assertRaisesRegex(
            ValueError, "SHA-256 mismatch: workspace/program.md"
        ):
            verify_campaign(self.root)

    def test_record_corruption(self):
        (self.root / "report.md").write_bytes(b"RESULTS-ONLY\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch: report.md"):
            verify_campaign(self.root)

    def test_unsafe_paths(self):
        for name in (
            "/absolute",
            "../escape",
            "workspace/../escape",
            "workspace\\escape",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)


if __name__ == "__main__":
    unittest.main()

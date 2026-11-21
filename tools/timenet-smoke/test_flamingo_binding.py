"""Comprobar que la nueva asociación conserva la procedencia de los dos roles."""

import json
import unittest

import test_direct_cohorts as fixtures
from flamingo_binding import CONFIG, WEIGHTS_SHA256, bind, digest


class FlamingoBindingTest(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.DirectCohortsTest()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.run_export()
        self.folder = fixture.dest
        self.protocol = fixture.protocol_path
        self.weights = CONFIG / "tslm-nov26-SHA256SUMS"
        self.root = self.folder / "manifest.json"
        self.release = digest(self.root)

    def bind(self):
        return bind(self.folder, self.release, self.protocol, self.weights)

    def test_preserves_phase_digests_and_excludes_scorer(self):
        (self.folder / "scorer").rename(self.folder / "unavailable")
        result = self.bind()
        self.assertEqual(result["weights_manifest_sha256"], WEIGHTS_SHA256)
        for role in ("fit", "inner_validation"):
            self.assertEqual(
                result["roles"][role], digest(self.folder / "trainer" / role / "manifest.json")
            )
        self.assertEqual(set(result["roles"]), {"fit", "inner_validation"})

    def test_wrong_base(self):
        self.weights = self.protocol
        with self.assertRaisesRegex(ValueError, "pesos"):
            self.bind()

    def test_mutated_payload(self):
        (self.folder / "trainer/fit/data.npz").write_bytes(b"otro")
        with self.assertRaisesRegex(ValueError, "Archivos"):
            self.bind()

    def test_phase_swap_even_if_root_is_rehashed(self):
        a, b = (self.folder / "trainer" / r / "manifest.json" for r in ("fit", "inner_validation"))
        a.write_bytes(b.read_bytes())
        record = json.loads(self.root.read_bytes())
        record["manifests"]["fit"] = digest(a)
        self.root.write_text(json.dumps(record))
        self.release = digest(self.root)
        with self.assertRaisesRegex(ValueError, "Contrato"):
            self.bind()

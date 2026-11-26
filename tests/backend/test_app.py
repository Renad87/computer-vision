"""Backend integration tests. Real-model tests skip when the ML stack or weights are unavailable (stdlib Python)."""
import io
import os
import unittest

try:
    from fastapi.testclient import TestClient
    from PIL import Image
    HAVE_STACK = True
except ImportError:  # stdlib-only interpreter
    HAVE_STACK = False

REAL_IMAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "external", "poetry_vision_old", "product",
                              "evaluation", "images")


def png(color=(30, 120, 200), size=(256, 256)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@unittest.skipUnless(HAVE_STACK, "FastAPI/PIL not installed")
class BackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend.app import app
        cls.ctx = TestClient(app)
        cls.client = cls.ctx.__enter__()
        cls.ready = cls.client.get("/api/ready").json()
        if not cls.ready["model"]["loaded"]:
            cls.ctx.__exit__(None, None, None)
            raise unittest.SkipTest(f"model not loadable here: {cls.ready['model']['error']}")

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None, None, None)

    def analyze(self, data, name="x.png"):
        return self.client.post("/api/analyze", files={"image": (name, data, "image/png")})

    def test_health_and_ready(self):
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")
        r = self.ready
        self.assertTrue(r["ready"])
        self.assertEqual(r["model"]["heads"]["emotion"]["origin"], "trained_poetry_vision_v1")
        self.assertGreater(r["corpus"]["count"], 0)
        self.assertNotIn("/Users/", str(r))

    def test_invalid_and_empty_images(self):
        self.assertEqual(self.analyze(b"not an image").json()["error"]["code"], "invalid_image")
        self.assertEqual(self.analyze(b"").json()["error"]["code"], "empty_file")
        self.assertEqual(self.analyze(png(size=(20, 20))).json()["error"]["code"], "too_small")

    def test_profile_reuse_and_modes(self):
        a = self.analyze(png())
        self.assertEqual(a.status_code, 200)
        aid = a.json()["analysis_id"]
        body = {"analysis_id": aid, "selected_lit_emotion": "lit_emotion.longing",
                "confirmed_visual_items": [{"id": "scene_group.desert", "user_selection": "focus"}]}
        dev = self.client.post("/api/recommend", json={**body, "mode": "development"}).json()
        self.assertTrue(dev["inference_reused"])
        self.assertIsNotNone(dev["disclosure_ar"])
        for item in dev["recommendations"]["items"]:
            self.assertIn("T_DRAFT_DISCLOSURE", item["explanation"]["template_ids"])
        prod = self.client.post("/api/recommend", json={**body, "mode": "production"}).json()
        self.assertIsNone(prod["disclosure_ar"])
        displayable = self.ready["corpus"]["displayable"]["production"]
        if displayable == 0:
            self.assertEqual(prod["recommendations"]["status"], "abstained")
            self.assertEqual(prod["recommendations"]["abstention"]["reason_code"], "empty_corpus")
        for item in prod["recommendations"]["items"]:
            self.assertIn(item["review_status"], ("reviewed", "double_reviewed", "adjudicated"))
        other = self.client.post("/api/recommend", json={**body, "mode": "development",
                                                         "selected_lit_emotion": "lit_emotion.pride"}).json()
        self.assertNotEqual([i["verse_id"] for i in dev["recommendations"]["items"]],
                            [i["verse_id"] for i in other["recommendations"]["items"]])

    def test_errors(self):
        r = self.client.post("/api/recommend", json={"analysis_id": "missing", "selected_lit_emotion": "lit_emotion.joy"})
        self.assertEqual(r.status_code, 404)
        aid = self.analyze(png()).json()["analysis_id"]
        r = self.client.post("/api/recommend", json={"analysis_id": aid, "selected_lit_emotion": "lit_emotion.nope"})
        self.assertEqual(r.status_code, 422)
        r = self.client.post("/api/recommend", json={"analysis_id": aid, "selected_lit_emotion": "lit_emotion.joy",
                                                     "confirmed_visual_items": [
                                                         {"id": "scene_group.sea", "user_selection": "focus"},
                                                         {"id": "scene_group.desert", "user_selection": "focus"}]})
        self.assertEqual(r.status_code, 422)

    @unittest.skipUnless(os.path.isdir(REAL_IMAGE_DIR), "real evaluation images not available")
    def test_real_desert_image(self):
        with open(os.path.join(REAL_IMAGE_DIR, "img_eval_desert2.jpg"), "rb") as fh:
            a = self.analyze(fh.read(), "desert.jpg").json()
        top = max(a["inference"]["scene"]["predictions"], key=lambda p: p["score"])
        self.assertEqual(top["id"], "scene.desert")
        self.assertEqual(a["suggestion"]["visual_items"][0]["id"], "scene_group.desert")


@unittest.skipUnless(HAVE_STACK, "FastAPI not installed")
class MissingArtifactsTest(unittest.TestCase):
    def test_missing_corpus_reported(self):
        from backend.service import State
        s = State()
        s.load_corpus("poetry_corpus/exports/does_not_exist.jsonl")
        r = s.readiness()
        self.assertFalse(r["ready"])
        self.assertIn("not found", r["corpus"]["error"])
        self.assertNotIn("/Users/", r["corpus"]["error"])


if __name__ == "__main__":
    unittest.main()

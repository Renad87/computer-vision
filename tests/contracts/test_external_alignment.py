"""The taxonomy matches the reused models' class orders (read-only checks against the original project)."""
import ast
import json
import os
import unittest
import zipfile

from contracts.taxonomy import load_taxonomy

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLD = os.environ.get("PV_OLD_PROJECT", os.path.join(REPO, "external", "poetry_vision_old"))
VISUAL = os.path.join(OLD, "product", "vendor", "visual_module", "ml", "visual")
RENAD_CONFIG = os.path.join(OLD, "team_modules", "emotion_keras_results", "emotion_keras", "model_config.json")


def npz_strings(path, key):
    """Read a 1-D unicode array from an uncompressed .npz without numpy."""
    with zipfile.ZipFile(path) as archive:
        raw = archive.read(key + ".npy")
    assert raw[:6] == b"\x93NUMPY"
    if raw[6] == 1:
        header_len, start = int.from_bytes(raw[8:10], "little"), 10
    else:
        header_len, start = int.from_bytes(raw[8:12], "little"), 12
    header = ast.literal_eval(raw[start:start + header_len].decode("latin1"))
    assert header["descr"].startswith("<U") and len(header["shape"]) == 1
    width, data = int(header["descr"][2:]), raw[start + header_len:]
    return [data[i * 4 * width:(i + 1) * 4 * width].decode("utf-32-le").rstrip("\x00")
            for i in range(header["shape"][0])]


@unittest.skipUnless(os.path.isdir(VISUAL), "original visual module not available")
class VisualModuleAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tax = load_taxonomy()

    def test_scene_head_class_order(self):
        names = npz_strings(os.path.join(VISUAL, "weights", "scene_head_clip.npz"), "classes")
        self.assertEqual(names, self.tax.external_names["scene"])
        self.assertEqual(["scene.other" if n == "__other__" else f"scene.{n}" for n in names],
                         self.tax.class_order["scene"])

    def test_tag_head_order(self):
        names = npz_strings(os.path.join(VISUAL, "weights", "tag_heads.npz"), "ids")
        self.assertEqual(names, self.tax.external_names["tag"])
        self.assertEqual([f"tag.{n}" for n in names], self.tax.class_order["tag"])

    def test_exposed_tags_are_the_validated_ones(self):
        with open(os.path.join(VISUAL, "results", "tag_metrics.json"), encoding="utf-8") as fh:
            metrics = json.load(fh)["tags"]
        self.assertEqual({f"tag.{k}" for k, v in metrics.items() if v.get("validated")}, set(self.tax.exposed_tags))

    def test_places365_lists_are_unchanged(self):
        with open(os.path.join(VISUAL, "taxonomy.json"), encoding="utf-8") as fh:
            visual = json.load(fh)
        mapping = self.tax.data["places365_mapping"]
        for scene in visual["scenes"]:
            self.assertEqual(scene["places365"], mapping[f"scene.{scene['id']}"])
        self.assertEqual(visual["background_places365"], mapping["background_for_scene_other"])
        self.assertEqual(visual["ood_places365"], mapping["ood_excluded"])


@unittest.skipUnless(os.path.isfile(RENAD_CONFIG), "Renad's model_config.json not available")
class EmotionModelAlignment(unittest.TestCase):
    def test_emotion_class_order(self):
        with open(RENAD_CONFIG, encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertEqual(config["classes"], load_taxonomy().external_names["img_emotion"])


if __name__ == "__main__":
    unittest.main()

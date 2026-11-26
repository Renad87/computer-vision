"""Arabic preprocessing (N0/N1/N2) and TF-IDF / cosine (RETRIEVAL_METHOD.md sections 1-2)."""
import math
import unittest

from retrieval.preprocess import NEGATIONS, normalize, tokenize
from retrieval.tfidf import LECTURE, SMOOTHED, TfidfModel, bag_of_words, cosine


class Preprocessing(unittest.TestCase):
    def test_required_examples(self):
        self.assertEqual(["بحر"], tokenize("وَالبَحرُ", "N1"))
        self.assertEqual(["صحراء"], tokenize("بِالصَّحراءِ", "N1"))
        self.assertEqual(["فابكي"], tokenize("فَأَبكي", "N1"))
        self.assertEqual(["ابكي"], tokenize("فَأَبكي", "N2"))

    def test_alef_maqsura_and_ta_marbuta_are_kept(self):
        self.assertEqual(["ليلى"], tokenize("لَيلى", "N0"))
        self.assertEqual(["ليلى"], tokenize("لَيلى", "N1"))
        self.assertEqual(["حياة"], tokenize("حَياةٌ", "N1"))
        # N2 would strip the first letter of the name (3 letters remain): evidence for the N1 default.
        self.assertEqual(["يلى"], tokenize("لَيلى", "N2"))

    def test_protected_words_in_n2(self):
        for word in ("فراق", "وداع", "وادي", "بكاء"):
            self.assertEqual([word], tokenize(word, "N2"), word)
        self.assertEqual(["فراق"], tokenize("وَالفِراقُ", "N2"))
        self.assertEqual(["بحر"], tokenize("وبحر", "N2"))  # an unprotected proclitic is stripped

    def test_negations_are_kept(self):
        for neg in NEGATIONS:
            for variant in ("N0", "N1", "N2"):
                self.assertIn(neg, tokenize(f"{neg} أَنسى", variant))
        self.assertNotIn("في", tokenize("في البحر", "N1"))  # a particle stop word is removed

    def test_n0_normalization(self):
        self.assertEqual("احمد امير اية", normalize("أَحمـــدُ، إِمير! آيَة"))
        verse = "لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ"
        self.assertNotIn("  ", normalize(verse))  # the 4-space hemistich gap becomes one space
        self.assertEqual("الصلاة", normalize("ٱلصَّلَاةُ"))  # alef wasla and superscript-free diacritics
        self.assertEqual("ابراهيم", normalize("إبراهٰيم"))  # U+0670 superscript alef removed

    def test_article_kept_when_too_short(self):
        self.assertEqual(["الله"], tokenize("الله", "N1"))  # "له" would leave fewer than 3 letters

    def test_original_text_is_not_modified(self):
        text = "وَالبَحرُ"
        tokenize(text, "N2")
        self.assertEqual("وَالبَحرُ", text)


class Tfidf(unittest.TestCase):
    DOCS = [["a", "b"], ["a", "c"], ["a", "b", "b"]]

    def test_smoothed_matches_hand_calculation(self):
        m = TfidfModel(self.DOCS, SMOOTHED)
        self.assertAlmostEqual(1.0, m.idf["a"])                       # ln(4/4) + 1
        self.assertAlmostEqual(math.log(4 / 3) + 1, m.idf["b"])       # df = 2
        self.assertAlmostEqual(math.log(2) + 1, m.idf["c"])           # df = 1
        wb = 2 * (math.log(4 / 3) + 1)                                # d3: tf(b) = 2
        self.assertAlmostEqual(1 / math.sqrt(1 + wb * wb), m.doc_vectors[2]["a"])
        q = m.vector({"b": 1})
        self.assertAlmostEqual(wb / math.sqrt(1 + wb * wb), cosine(q, m.doc_vectors[2]))
        self.assertEqual(0.0, cosine(q, m.doc_vectors[1]))

    def test_lecture_formula_and_nonpositive_idf(self):
        m = TfidfModel(self.DOCS, LECTURE)
        self.assertAlmostEqual(math.log(3 / 4), m.idf["a"])  # in every document: IDF < 0
        self.assertAlmostEqual(0.0, m.idf["b"])              # df = N - 1: IDF = 0
        self.assertAlmostEqual(math.log(3 / 2), m.idf["c"])
        self.assertEqual(["a", "b"], m.nonpositive_idf_terms())
        self.assertLessEqual(m.idf["a"], 0)

    def test_tf_length_normalization_does_not_change_cosine(self):
        m = TfidfModel(self.DOCS, SMOOTHED)
        counts = bag_of_words(["a", "b", "b", "c"])
        scaled = {t: c / 4 for t, c in counts.items()}
        for a, b in zip(sorted(m.vector(counts).items()), sorted(m.vector(scaled).items())):
            self.assertEqual(a[0], b[0])
            self.assertAlmostEqual(a[1], b[1])

    def test_cosine_range_and_identity(self):
        m = TfidfModel(self.DOCS, SMOOTHED)
        for d in m.doc_vectors:
            self.assertAlmostEqual(1.0, cosine(d, d))
            for e in m.doc_vectors:
                self.assertGreaterEqual(cosine(d, e), 0.0)

    def test_out_of_vocabulary_query(self):
        m = TfidfModel(self.DOCS, SMOOTHED)
        self.assertEqual({}, m.vector({"zzz": 1}))
        self.assertEqual(0.0, cosine({}, m.doc_vectors[0]))


if __name__ == "__main__":
    unittest.main()

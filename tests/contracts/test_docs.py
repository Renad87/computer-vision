"""Generated documentation stays in sync with the validator specs."""
import os
import unittest

from contracts.tools.render_fields import OUT, render


class FieldReference(unittest.TestCase):
    def test_contract_fields_md_is_up_to_date(self):
        with open(OUT, encoding="utf-8") as fh:
            on_disk = fh.read()
        self.assertEqual(render(), on_disk, "regenerate with python3 -m contracts.tools.render_fields")

    def test_every_documented_error_code_exists(self):
        from contracts.schema import ERROR_CODES
        with open(os.path.join(os.path.dirname(OUT), "CONTRACTS.md"), encoding="utf-8") as fh:
            text = fh.read()
        for code in ERROR_CODES:
            self.assertIn(f"`{code}`", text)


if __name__ == "__main__":
    unittest.main()

"""Poetry Vision unified image dataset (M2): data preparation for the `image_manifest` contract.

Entry points (run from the package root):
    python -m data_preparation.build v0.9 [--workdir DIR] [--emoset-zip PATH]
    python -m data_preparation.build v1   [--workdir DIR] [--emoset-zip PATH] [--places-dir PATH] ...
    python -m data_preparation.layout     [--workdir DIR] [--emoset-zip PATH] [--places-dir PATH]
    python -m data_preparation.verify_images <manifest> [--workdir DIR]
    python -m data_preparation.reader <manifest>

--workdir is the folder holding external/ (inputs) and datasets/ (outputs). It defaults to the package root as in
ASSET_CHECKLIST.md. Keep it outside the package if you run verify_package.py, whose bundled scan rejects images,
zips and files over 1 MB anywhere in the package.
"""

"""Reproduce the packaged SentiWordNet subset from NLTK's official corpus.

Normal analysis never downloads anything. This script is only for resource
maintenance when the controlled opinion vocabulary changes.
"""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/sentiwordnet.zip"
SOURCE_SHA256 = "b66876a17aaeb4c7c7c8d2f5bb2cf91fde16e1b76e2421e5480fedd17ad248c1"


def prepare(download: bool = False) -> None:
    source = ROOT / "data" / "vendor" / "sentiwordnet.zip"
    if download:
        source.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != SOURCE_SHA256:
            raise ValueError("The upstream corpus checksum changed; inspect it before updating the pin.")
        source.write_bytes(payload)
    if not source.exists():
        raise FileNotFoundError("Corpus archive missing. Run this script with --download once.")
    payload = source.read_bytes()
    if hashlib.sha256(payload).hexdigest() != SOURCE_SHA256:
        raise ValueError("The cached corpus does not match the verified upstream checksum.")
    resource_dir = ROOT / "hotel_compiler" / "resources"
    vocabulary = json.loads((resource_dir / "domain.json").read_text(encoding="utf-8"))
    required = {spec["synset"] for spec in vocabulary["opinions"].values()}
    required.update(context["synset"] for spec in vocabulary["opinions"].values()
                    for context in spec.get("category_senses", {}).values())
    with zipfile.ZipFile(source) as archive:
        original = archive.read("sentiwordnet/SentiWordNet_3.0.0.txt").decode("utf-8")
        original_readme = archive.read("sentiwordnet/README.txt").decode("utf-8")
    header, selected, found = [], [], set()
    for line in original.splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line:
            fields = line.split("\t", 5)
            key = f"{fields[0]}:{fields[1]}"
            if key in required:
                selected.append(line)
                found.add(key)
    if found != required:
        raise ValueError(f"Unknown source synsets: {sorted(required - found)}")
    subset = ("\n".join(header + ["# Project subset: selected original rows, with unchanged scores."] + selected) + "\n").encode("utf-8")
    (resource_dir / "sentiwordnet.tsv").write_bytes(subset)
    (resource_dir / "SENTIWORDNET_LICENSE.txt").write_text(
        original_readme + "\nThe bundled TSV is an extracted subset of this resource. "
        "Original rows and scores are unchanged. This subset remains under CC BY-SA 3.0.\n"
        "License: https://creativecommons.org/licenses/by-sa/3.0/\n",
        encoding="utf-8",
    )
    provenance = {
        "resource": "SentiWordNet 3.0.0",
        "source_url": SOURCE_URL,
        "source_archive_sha256": SOURCE_SHA256,
        "subset_sha256": hashlib.sha256(subset).hexdigest(),
        "selected_synsets": len(selected),
        "opinion_terms": len(vocabulary["opinions"]),
        "license": "CC BY-SA 3.0",
        "selection": "Exact POS/offset IDs in domain.json; original rows and scores are unchanged.",
        "reference": "Baccianella, Esuli, Sebastiani (2010). SentiWordNet 3.0: An Enhanced Lexical Resource for Sentiment Analysis. LREC.",
    }
    (resource_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(selected)} genuine SentiWordNet synsets for {len(vocabulary['opinions'])} controlled opinion terms.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Fetch the pinned official corpus archive.")
    prepare(parser.parse_args().download)


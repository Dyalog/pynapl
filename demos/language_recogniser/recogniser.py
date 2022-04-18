"""
Automatic detection of natural language used in a text.

Use this program as a CLI.
Without arguments, enters into a REPL that recognises sentences.
"""

import argparse
import csv
import math
import pathlib
import sys
from typing import List

from pynapl.APL import APL
from pynapl.APLPyConnect import Connection

LANGUAGES = ["en", "fr", "es", "pt"]
DATA_FOLDER = pathlib.Path(__file__).parent / "data"
FILE_NAME_TEMPLATE = "{lang}_trigram_count_filtered.tsv"


def init_data(apl: Connection.APL) -> List[int]:
    """Initialise the data arrays on the APL side.

    As a side effect, this function defines some arrays on the APL instance.
    For each language, {lang}_trigrams and {lang}_counts arrays are created.
    The trigrams array is a nested character vector,
    and the counts array is a simple integer vector.
    The counts vector is one item longer than the trigrams array,
    having an extra 1 at the end.

    Returns an integer list, with the total trigram count for each language.
    """

    totals = []
    for lang in LANGUAGES:
        total = 0
        trigrams, counts = [], []
        with open(DATA_FOLDER / FILE_NAME_TEMPLATE.format(lang=lang), "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for trigram, count in reader:
                trigrams.append(trigram)
                total += int(count)
                counts.append(int(count) + 1)
        totals.append(total)

        _ = apl.eval(f"{lang}_trigrams ← ⊃∆", trigrams)
        _ = apl.eval(f"{lang}_counts ← 1,⍨⊃∆", counts)

    return totals


def get_counts(apl: Connection.APL, sentence: str, language: str) -> List[int]:
    """Return the trigram counts for each trigram of a sentence."""
    code = "{lang}_counts[{lang}_trigrams ⍳ 3,/⊃∆]".format(lang=language)
    return apl.eval(code, sentence.lower())


def recognise_sentence(apl: Connection.APL, totals: List[int], sentence: str) -> str:
    """Performs automatic language recognition on the given sentence."""

    log_probabilities = [
        sum(math.log(c / total) for c in get_counts(apl, sentence.lower(), lang))
        for lang, total in zip(LANGUAGES, totals)
    ]
    # Find the index where log_probabilities is maximal and return respective language.
    return LANGUAGES[max(range(len(LANGUAGES)), key=log_probabilities.__getitem__)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sentence", help="Sentence to recognise.")
    parser.add_argument(
        "-i", "--interactive", help="Enter interactive mode.", action="store_true"
    )
    args = parser.parse_args()

    if not args.sentence and not args.interactive:
        sys.exit()

    apl = APL()
    totals = init_data(apl)

    if args.sentence:
        print(recognise_sentence(apl, totals, args.sentence))
    if args.interactive:
        print("Type sentences to be recognised:")
        sentence = input(" >> ")
        while sentence:
            print(recognise_sentence(apl, totals, sentence))
            sentence = input(" >> ")

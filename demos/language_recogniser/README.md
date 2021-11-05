# Natural language recognition

This demo uses a frequency approach to detecting the natural language of a piece of text.

The `data` folder contains frequency counts of trigrams (sequences of three characters)
in texts written in English, French, Portuguese, and Spanish.

The program uses the Naive Bayes theorem to inspect the trigrams
of the input sentence and determine what is the language that the
sentence is more likely to belong to.

The Python program makes use of APL to process the input sentence,
breaking it up into trigrams and doing the Naive Bayes computations.

One particularly interesting thing about this demo is that,
even though the program is driven by Python,
all data is kept on the APL side.


## Run this demo

This demo is implemented as a CLI, so simply run `python recogniser.py --help` to get help.

An example usage follows:

```bash
python recogniser.py --sentence "My name is Charles"
```

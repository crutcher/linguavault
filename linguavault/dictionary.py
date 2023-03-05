import argparse
import sys
from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass

from linguavault.api_utils import completion, load_openai_secrets
from linguavault.format_cleaners import paranoid_json, reblock

PHONETICS_PREFIX = """
You are a dictionary.

You will be given a source language, and a term (a word or phrase)
from that source language. You will be given an example usage of that term.

Some words are heteronyms, with different pronunciations for different
senses and usages. To distinguish, and select the correct pronunciation,
you will be given the part of speech of the term sense, and a short definition of the term sense.

The goal is to produce an IPA phonetic alphabet pronunciation and an phonetic spelling
for the correct form of the term matching the given part of speech and definition.

If there is rhyming word for the given pronunciation, include it as well.

Example Input 1:
Language: Italian
Term: gelato
Part of Speech: noun
Definition: Italian-style ice cream.
Example Usage: "We went to the shops for some gelato."

Example Result 1:
IPA Phonetic Pronunciation:  /d͡ʒəˈlɑtoʊ/
Phonetic Spelling: jeh-LAH-toh

Example Input 2:
Language: English
Term: live
Part of Speech: adjective
Definition: being alive
Example Usage: "The website is live."

Example Result 2:
IPA Phonetic Pronunciation: /laɪv/
Phonetic Spelling: lyv
Rhymes With: thrive
"""


@dataclass
class Phonetics:
    term: str
    ipa: Optional[str] = None
    phonetic_spelling: Optional[str] = None
    rhymes_with: Optional[str] = None

    def empty(self) -> bool:
        return not any(
            [
                self.ipa,
                self.phonetic_spelling,
                self.rhymes_with,
            ]
        )

    def __str__(self) -> str:
        ps = []
        if self.ipa:
            ps.append(f"/{self.ipa}/")
        if self.phonetic_spelling:
            ps.append(f'"{self.phonetic_spelling}"')
        if self.rhymes_with:
            ps.append(f'rhymes with "{self.rhymes_with}"')
        return ", ".join(ps)


def get_sense_phonetics(
    term: str,
    term_language: str,
    part_of_speech: str,
    definition: str,
    example_usage: str,
) -> Phonetics:
    query = [
        f"Language: {term_language}",
        f"Term: {term}",
        f"Part of Speech: {part_of_speech}",
        f"Definition: {definition}",
        f"Example Usage: {example_usage}",
    ]
    answer = completion(PHONETICS_PREFIX, "\n".join(query))

    phonetics = Phonetics(term=term)
    for line in answer.strip().splitlines():
        try:
            key, val = line.split(":", 1)
        except ValueError:
            continue
        val = val.strip()

        if "ipa" in key.lower():
            if val.startswith("/"):
                val = val[1:]
            if val.endswith("/"):
                val = val[:-1]
            phonetics.ipa = val
        if "spelling" in key.lower():
            phonetics.phonetic_spelling = val
        if "rhymes" in key.lower():
            phonetics.rhymes_with = val

    return phonetics


COMMON_PREFIX = """
You are a dictionary of all the world's languages.

Your definitions should be accurate to common usage, but also informal and cheeky, humorous and anti-authoritarian.

Include professional, popular, urban, and technical senses for the words.
Include newer popular slang and idiom senses.
Try hard to include all well-known senses of a term.

The user will provide a prompt; and you should respond with a well-formed structured JSON result.
Do not produce any text other than the structured result output.

The term language (the language the term is defined in) will be provided by the user.
The desired output language for the results to be written in will be provided by the user.
The term itself will be provided by the user.

Optional term contexts may be provided to specify contexts in which the term is found.
"""

DEFINE_PREFIX = (
    COMMON_PREFIX
    + """
The structure of the input is:
TermLanguage: $TermLanguage
OutputLanguage: $OutputLanguage
Term: $Term
[
TermContext: $TermContext1
TermContext: $TermContext2
...
]

The structure of the language object should be well-formed JSON:
{
  "term": <Term>,
  "term_language": <Term Language>,
  "output_language": <Output Language>,
  "senses": [
    {
      "part_of_speech": <Part of Speech>,
      "short_definition": <Short Definition written in the given Output Language>,
      "term_context": <TermContext, or null>
    }
    < Additional Senses ... >
  ]
}
"""
)


@dataclass
class TermSenseSummary:
    part_of_speech: str
    short_definition: str
    term_context: Optional[str]


@dataclass
class TermListing:
    term: str
    term_language: str
    output_language: str
    senses: list[TermSenseSummary]


def get_term_listing(
    term: str,
    term_language: str = "English",
    term_contexts: Optional[list[str]] = None,
    output_language: str = "English",
) -> tuple[TermListing, str]:
    query = [
        f"TermLanguage: {term_language}",
        f"OutputLanguage: {output_language}",
        f"Term: {term}",
    ]
    if term_contexts:
        for context in term_contexts:
            query.append(f"TermContext: {context}")

    answer = completion(DEFINE_PREFIX, "\n".join(query))
    try:
        schema = marshmallow_dataclass.class_schema(TermListing)()
        return schema.load(paranoid_json(answer)), answer
    except Exception as e:
        raise ValueError(answer) from e


SENSE_PREFIX = (
    COMMON_PREFIX
    + """
The user will provide a query with the short-definition of one sense of a term.

You will produce structured information about that one sense; and not
other senses of the term.

Example 1:
TermLanguage: <TermLanguage>
OutputLanguage: <OutputLanguage>
Term: <Term>
PartOfSpeech: <PartOfSpeech>
ShortDefinition: <ShortDefinition>

Example 2:
TermLanguage: <TermLanguage>
OutputLanguage: <OutputLanguage>
Term: <Term>
PartOfSpeech: <PartOfSpeech>
ShortDefinition: <ShortDefinition>
TermContext: <TermContext>


The structure of the language object should be:
{
  "part_of_speech": <Part of Speech>,
  "term_context": <TermContext, or null>,
  "keywords": [<Keyword of contexts where the word-sense might be seen> ...],
  "popularity": <Degree of Popularity as a float from 0.0 to 1.0>,
  "formality": <Degree of Formality as a float from 0.0 to 1.0>,
  "vulgarity": <Degree of Vulgarity as a float from 0.0 to 1.0>,
  "synonyms": [<Synonym> ...],
  "antonyms": [<Antonym; term that means the opposite of the sense> ...],
  "long_definition": <Long Definition (~500 words) written in the given Output Language>,
  "example_usage": <Example Sentence written in the given Term Language>
}

Try hard to include all well-known senses of a term.
Do not produce any text other than the JSON output.
"""
)


@dataclass
class TermSenseDefinition:
    part_of_speech: str
    popularity: float
    formality: float
    vulgarity: float
    long_definition: str
    example_usage: str
    term_context: Optional[str] = None
    keywords: Optional[list[str]] = None
    synonyms: Optional[list[str]] = None
    antonyms: Optional[list[str]] = None


def get_sense_definition(
    term: str,
    part_of_speech: str,
    short_def: str,
    term_context: Optional[str] = None,
    term_language: str = "English",
    output_language: str = "English",
) -> tuple[TermSenseDefinition, str]:
    query = [
        f"TermLanguage: {term_language}",
        f"OutputLanguage: {output_language}",
        f"Term: {term}",
        f"PartOfSpeech: {part_of_speech}",
        f"ShortDefinition: {short_def}",
    ]
    if term_context:
        query.append(f"TermContext: {term_context}")

    answer = completion(SENSE_PREFIX, "\n".join(query))
    try:
        schema = marshmallow_dataclass.class_schema(TermSenseDefinition)()
        data = paranoid_json(answer)
        if not data.get("example_usage"):
            data["example_usage"] = "N/A"
        if not data.get("part_of_speech"):
            data["part_of_speech"] = "unknown"
        return schema.load(data), answer
    except Exception as e:
        raise ValueError(answer) from e


SYNONYM_PREFIX = """
You are a dictionary.

You will be given a base term (a word or phrase) and a short definition
for one sense (or meaning) of that term, and a comparison term which is
known to be a synonym to that sense of the base term; write a short
(1-3 sentence) contrast between the words in the given sense;
in the style of a concise writing language style guide.

You will be given the language the Term is from,
as well as the target language that the output should be written in.

Example Input:
Term: susurrus
Term Language: English
Sense Definition: soft murmuring or rustling in quality
Synonym: hushed
Output Language: English

Example Result:
While both "susurrus" and "hushed" describe soft, low sounds, "susurrus"
has a more specific connotation of a gentle rustling or whispering,
whereas "hushed" can refer to any low volume sound that is quiet or subdued.
"""


def get_synonym_comparison(
    term: str,
    short_def: str,
    synonym: str,
    term_language: str = "English",
    output_language: str = "English",
) -> str:
    query = [
        f"Term: {term}",
        f"Term Language: {term_language}",
        f"ShortDefinition: {short_def}",
        f"Synonym: {synonym}",
        f"Output Language: {output_language}",
    ]

    return reblock(completion(SYNONYM_PREFIX, "\n".join(query)))


ANTONYM_PREFIX = """
You are a dictionary.
You will be given a base term (a word or phrase) and a short definition for one sense
(or meaning) of that term, and a comparison term which is known to be a antonym to that
sense of the base term; write a short (1-3 sentence) contrast between the words in the
given sense; in the style of a concise writing language style guide.

You will be given the language the Term is from,
as well as the target language that the output should be written in.

Example Input:
Term: sussurus
Sense Definition: a whispering, murmuring sound
Antonym: clamour

Example Result:
"sussurus" refers to a gentle, hushed sound of whispering or murmuring, while "clamour"
refers to a loud, noisy, and chaotic sound of shouting or protesting.
"""


def get_antonym_comparison(
    term: str,
    short_def: str,
    antonym: str,
    term_language: str = "English",
    output_language: str = "English",
) -> str:
    query = [
        f"Term: {term}",
        f"Term Language: {term_language}",
        f"ShortDefinition: {short_def}",
        f"Antonym: {antonym}",
        f"Output Language: {output_language}",
    ]

    return reblock(completion(ANTONYM_PREFIX, "\n".join(query)))


def query(
    term: str,
    term_language: str = "English",
    output_language: str = "English",
    term_contexts: Optional[list[str]] = None,
):
    term_listing, _raw = get_term_listing(
        term=term,
        term_language=term_language,
        term_contexts=term_contexts,
        output_language=output_language,
    )
    print(
        " :: ".join(
            [
                "# Werdsonary",
                "Define",
                f'"{term_listing.term}"',
                f"{term_listing.term_language}",
            ]
        )
    )
    print(f"  * Dictionary Language: {term_listing.output_language}")

    for sense in term_listing.senses:
        sense_info, _raw = get_sense_definition(
            term=term_listing.term,
            part_of_speech=sense.part_of_speech,
            short_def=sense.short_definition,
            term_context=sense.term_context,
            term_language=term_language,
            output_language=output_language,
        )
        print()
        print(
            f'## Sense: "{term_listing.term}", {sense.part_of_speech.lower()} : {sense.short_definition}'
        )

        phonetics = get_sense_phonetics(
            term=term_listing.term,
            term_language=term_listing.term_language,
            part_of_speech=sense.part_of_speech,
            definition=sense.short_definition,
            example_usage=sense_info.example_usage,
        )
        if not phonetics.empty():
            print(f"  * Pronounced: {phonetics}")

        usage = []
        if sense_info.term_context:
            usage.append(sense_info.term_context)
        if sense_info.keywords:
            usage.append(", ".join(sense_info.keywords))
        usage.append(
            f"popularity={sense_info.popularity}, "
            f"formality={sense_info.formality}, "
            f"vulgarity={sense_info.vulgarity}"
        )
        print("  * Usage:", " : ".join(usage))

        if sense_info.synonyms:
            print(f"  * Synonyms: {', '.join(repr(t) for t in sense_info.synonyms)}")
        if sense_info.antonyms:
            print(f"  * Antonyms: {', '.join(repr(t) for t in sense_info.antonyms)}")
        print(f'  * Example: "{sense_info.example_usage}"')
        print()
        print(sense_info.long_definition.strip())

        if sense_info.synonyms:
            for syn in sense_info.synonyms:
                print()
                print(f'### Synonym: "{term_listing.term}" ~= "{syn}"')
                comp = get_synonym_comparison(
                    term=term_listing.term,
                    short_def=sense.short_definition,
                    synonym=syn,
                    term_language=term_listing.term_language,
                    output_language=term_listing.output_language,
                )
                print(comp)

        if sense_info.antonyms:
            for ant in sense_info.antonyms:
                print()
                print(f'### Antonym: "{term_listing.term}" vs "{ant}"')
                comp = get_antonym_comparison(
                    term=term_listing.term,
                    short_def=sense.short_definition,
                    antonym=ant,
                    term_language=term_listing.term_language,
                    output_language=term_listing.output_language,
                )
                print(comp)


def main(argv):
    p = argparse.ArgumentParser(prog="dictionary")
    p.add_argument("--secrets_file", default=None)
    p.add_argument("term", help="The term to define")
    p.add_argument(
        "-c",
        "--term_context",
        nargs="*",
        help="Additional contexts the term is found in.",
    )
    p.add_argument(
        "--term_language",
        default="English",
        help="The language the term is in.",
    )
    p.add_argument(
        "--output_language",
        default="English",
        help="The language the output should be written in.",
    )
    args = p.parse_args(argv)

    load_openai_secrets(args.secrets_file)

    term_contexts = list(args.term_context or [])

    query(
        term=args.term,
        term_language=args.term_language,
        term_contexts=term_contexts,
        output_language=args.output_language,
    )
    print()


if __name__ == "__main__":
    main(sys.argv[1:])

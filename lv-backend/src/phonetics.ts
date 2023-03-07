import { getCompletion } from "./openai_utils";
import { AssertionError } from "assert";
import { OpenAIApi } from "openai";

const PHONETICS_PREFIX: string = `
You are a dictionary.

You will be given a source language, and a term (a word or phrase)
from that source language. You will be given an example usage of that term.

Some words are heteronyms, with different pronunciations for different
senses and usages. To distinguish, and select the correct pronunciation,
you will be given the part of speech of the term sense, and a short definition of the term sense.

The goal is to produce an IPA phonetic alphabet pronunciation and an phonetic spelling
for the correct form of the term matching the given part of speech and definition.

If there is rhyming word for the given pronunciation, include it as well.

Return only Key/Value Results.

Example Input 1:
Language: Italian
Term: gelato
Part of Speech: noun
Definition: Italian-style ice cream.
Example Usage: "We went to the shops for some gelato."

Example Result 1:
IPA: /d͡ʒəˈlɑtoʊ/
Spelling: jeh-LAH-toh

Example Input 2:
Language: English
Term: live
Part of Speech: adjective
Definition: being alive
Example Usage: "The website is live."

Example Result 2:
IPA: /laɪv/
Spelling: lyv
Rhymes: thrive
`;

interface PhoneticsParams {
  openai: OpenAIApi;
  term: string;
  termLanguage: string;
  partOfSpeech: string;
  definition: string;
  example_usage: string;
}

interface Phonetics {
  term: string;
  ipa?: string;
  spelling?: string;
  rhymesWith?: string;
}

export async function getPhonetics(
  options: PhoneticsParams
): Promise<Phonetics> {
  let query = [
    `Language: ${options.termLanguage}`,
    `Term: ${options.term}`,
    `Part of Speach: ${options.partOfSpeech}`,
    `Definition: ${options.definition}`,
    `Example Usage: ${options.example_usage}`,
  ].join("\n");
  const content = await getCompletion({
    openai: options.openai,
    prompt: PHONETICS_PREFIX,
    query,
  });
  if (content === null || content === undefined) {
    throw new AssertionError({ message: "failed" });
  }
  let phonetics: Phonetics = {
    term: options.term,
  };
  for (const line of content.split("\n")) {
    let parts = line.split(":", 2);
    if (parts.length == 2) {
      const key = parts[0].toLowerCase();
      const val = parts[1].trim();
      if (key.includes("ipa")) {
        phonetics.ipa = val;
      }
      if (key.includes("spelling")) {
        phonetics.spelling = val;
      }
      if (key.includes("rhymes")) {
        phonetics.rhymesWith = val;
      }
    }
  }
  return phonetics;
}


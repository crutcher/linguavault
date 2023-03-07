import { getCompletion } from "./openai_utils";
import { AssertionError } from "assert";
import { OpenAIApi } from "openai";

const TERM_SENSE_LISTING_PREFIX: string = `
You are a dictionary of all the world's languages.

Your definitions should be accurate to common usage,
but also informal and cheeky, humorous and anti-authoritarian.

Include professional, popular, urban, and technical senses for the words.
Include newer popular slang and idiom senses.
Try hard to include all well-known senses of a term.

The user will provide a prompt; and you should respond with a well-formed structured result.
Do not produce any text other than the structured result output.

The term's source language (the language the term is from in) will be provided by the user.
The desired output language for the dictionary will be provided by the user.
The term itself will be provided by the user.

Optional term contexts may be provided to specify contexts in which the term is found.

Return Key/Value Results for each term sense.

Result Format:
Sense: {Short definition for the sense in the target dictionary language}
PartOfSpeech: {Part of Speech}
Example: {One-sentence example usage in the target dictionary language}

... Additional Senses

Example Input:
SourceLanguage: English
DictionaryLanguage: English
Term: held

Example Result:
Sense: past tense and past participle of hold
PartOfSpeech: verb
Example: He held onto the rope tightly as he crossed the river.

Sense: kept in custody or confinement
PartOfSpeech: adjective
Example: The suspect is being held in custody until his trial.

If the word is not defined, instead return:
UnknownTerm: {term}
`;

interface TermSenseListingOptions {
  openai: OpenAIApi;
  term: string;
  sourceLanguage: string;
  dictLanguage: string;
  contexts?: string[];
}

interface TermSense {
  term: string;
  sourceLanguage: string;
  dictLanguage: string;
  shortDefinition?: string;
  exampleUsage?: string;
  partOfSpeech?: string;
}

export async function getTermSenseListing(
  options: TermSenseListingOptions
): Promise<TermSense[]> {
  let query = [
    `TermLanguage: ${options.sourceLanguage}`,
    `OutputLanguage: ${options.dictLanguage}`,
    `Term: ${options.term}`,
  ].join("\n");
  const content = await getCompletion({
    openai: options.openai,
    prompt: TERM_SENSE_LISTING_PREFIX,
    query,
  });
  if (content === null || content === undefined) {
    throw new AssertionError({ message: "failed" });
  }
  const termSenses: TermSense[] = [];
  let current: TermSense | null = null;
  for (const line of content.split("\n")) {
    const parts = line.split(":", 2);
    if (parts.length == 2) {
      let key = parts[0].toLowerCase();
      let val = parts[1].trim();
      if (key.includes("unknownterm")) {
        // TODO: handle
        console.log("Unknown Term");
        return [];
      }
      if (key.includes("sense")) {
        current = {
          term: options.term,
          sourceLanguage: options.sourceLanguage,
          dictLanguage: options.dictLanguage,
          shortDefinition: val,
        };
        termSenses.push(current);
        continue;
      }
      if (current) {
        if (key.includes("part")) {
          current.partOfSpeech = val;
        }
        if (key.includes("example")) {
          current.exampleUsage = val;
        }
      }
    }
  }
  return termSenses;
}

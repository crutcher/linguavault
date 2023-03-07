import { OpenAIApi } from "openai";
import { AssertionError } from "assert";

interface CompletionParams {
  openai: OpenAIApi;
  prompt: string;
  query: string;
}

export async function getCompletion({
  openai,
  prompt,
  query,
}: CompletionParams) {
  const content = await openai.createChatCompletion({
    model: "gpt-3.5-turbo",
    messages: [
      { role: "system", content: prompt },
      { role: "user", content: query },
    ],
  });
  return content?.data?.choices[0]?.message?.content;
}

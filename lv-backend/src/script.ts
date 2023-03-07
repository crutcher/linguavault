import { PrismaClient } from "@prisma/client";
import { Configuration, OpenAIApi } from "openai";
import { getTermSenseListing } from "./term_senses";

const prisma = new PrismaClient();

async function main() {
  const openai = new OpenAIApi(
    new Configuration({
      organization: process.env.OPENAI_ORGANIZATION,
      apiKey: process.env.OPENAI_API_KEY,
    })
  );
  const termSenses = await getTermSenseListing({
    openai: openai,
    term: "jshaoobay",
    sourceLanguage: "English",
    dictLanguage: "Pirate",
  });
  console.log(termSenses);
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });

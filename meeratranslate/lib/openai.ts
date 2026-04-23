import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Tone-specific instructions injected into every prompt
const TONE_INSTRUCTIONS: Record<string, string> = {
  eerie:
    "The tone should feel eerie and unsettling — quiet dread, strange imagery, a sense that something is deeply wrong beneath the surface.",
  haunting:
    "The tone should be haunting and melancholic — linger on emotions, let sentences echo, make readers feel the weight of what is left unsaid.",
  thriller:
    "The tone should be fast-paced and gripping — short punchy sentences, rising tension, urgency that keeps readers turning pages.",
  suspense:
    "The tone should build suspense — slow reveal, careful detail, every sentence should make the reader feel something is about to go terribly wrong.",
};

/**
 * Translates a single chunk of Hindi text to English using GPT.
 * Called sequentially for each chunk of a large document.
 */
export async function translateChunk(
  hindiText: string,
  tone: string,
  chunkIndex: number,
  totalChunks: number,
  previousContext?: string // last ~200 words of the previous chunk for continuity
): Promise<string> {
  const toneInstruction =
    TONE_INSTRUCTIONS[tone] || TONE_INSTRUCTIONS["thriller"];

  const contextNote =
    chunkIndex > 0 && previousContext
      ? `For context, here is the end of the previous section (do not re-translate this, just use it for flow):\n"${previousContext}"\n\n`
      : "";

  const systemPrompt = `You are a professional literary translator specializing in psychological thriller novels.
Your task is to translate Hindi text into clear, natural, human-like English that reads like it was originally written in English.

Rules:
- Never translate literally word-for-word
- Preserve the emotional depth, psychological tension, and meaning of the original
- Keep sentences natural and easy to read for English book readers
- Do not add explanations or annotations
- Output only the translated English text, nothing else
- ${toneInstruction}`;

  const userPrompt = `${contextNote}Translate the following Hindi text into English. This is chunk ${chunkIndex + 1} of ${totalChunks}.

${hindiText}`;

  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    temperature: 0.7, // slightly creative for literary quality
    max_tokens: 4000,
  });

  return response.choices[0].message.content?.trim() ?? "";
}

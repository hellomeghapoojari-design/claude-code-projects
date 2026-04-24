import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

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

export async function translateChunk(
  hindiText: string,
  tone: string,
  chunkIndex: number,
  totalChunks: number,
  previousContext?: string
): Promise<string> {
  const toneInstruction = TONE_INSTRUCTIONS[tone] || TONE_INSTRUCTIONS["thriller"];

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

  const response = await anthropic.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 4000,
    system: systemPrompt,
    messages: [{ role: "user", content: userPrompt }],
  });

  const block = response.content[0];
  return block.type === "text" ? block.text.trim() : "";
}

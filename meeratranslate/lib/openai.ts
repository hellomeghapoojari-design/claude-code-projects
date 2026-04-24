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
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) throw new Error("GROQ_API_KEY is not set in Railway Variables.");

  const toneInstruction = TONE_INSTRUCTIONS[tone] || TONE_INSTRUCTIONS["thriller"];
  const contextNote =
    chunkIndex > 0 && previousContext
      ? `For context, here is the end of the previous section (do not re-translate this, just use it for flow):\n"${previousContext}"\n\n`
      : "";

  const systemPrompt = `You are a professional literary translator specializing in psychological thriller novels.
Translate Hindi text into clear, natural, human-like English that reads like it was originally written in English.

Rules:
- Never translate literally word-for-word
- Preserve the emotional depth, psychological tension, and meaning of the original
- Keep sentences natural and easy to read for English book readers
- Do not add explanations or annotations
- Output only the translated English text, nothing else
- ${toneInstruction}`;

  const userPrompt = `${contextNote}Translate the following Hindi text into English. This is chunk ${chunkIndex + 1} of ${totalChunks}.

${hindiText}`;

  const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "llama-3.3-70b-versatile",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.7,
      max_tokens: 4000,
    }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error?.message || "Translation failed");
  return data.choices[0]?.message?.content?.trim() ?? "";
}

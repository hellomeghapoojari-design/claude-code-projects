/**
 * Splits large text into chunks of approximately `wordsPerChunk` words.
 * Splits on sentence boundaries (. ! ?) where possible to avoid
 * cutting mid-sentence and breaking the narrative flow.
 */
export function chunkText(
  text: string,
  wordsPerChunk: number = 2500
): string[] {
  if (!text.trim()) return [];

  // Normalise whitespace
  const cleaned = text.replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n");

  // Split on sentence-ending punctuation followed by space or newline
  const sentences = cleaned.split(/(?<=[।.!?])\s+/);

  const chunks: string[] = [];
  let currentChunk: string[] = [];
  let currentWordCount = 0;

  for (const sentence of sentences) {
    const wordCount = sentence.trim().split(/\s+/).length;

    // If adding this sentence would exceed the limit, flush the current chunk
    if (currentWordCount + wordCount > wordsPerChunk && currentChunk.length > 0) {
      chunks.push(currentChunk.join(" ").trim());
      currentChunk = [];
      currentWordCount = 0;
    }

    currentChunk.push(sentence);
    currentWordCount += wordCount;
  }

  // Push any remaining text as the final chunk
  if (currentChunk.length > 0) {
    chunks.push(currentChunk.join(" ").trim());
  }

  return chunks;
}

/**
 * Returns the last N words of a string — used as context for the next chunk
 * so the AI maintains narrative continuity across chunk boundaries.
 */
export function getContextTail(text: string, words: number = 150): string {
  const allWords = text.trim().split(/\s+/);
  return allWords.slice(-words).join(" ");
}

/**
 * Count words in a string (works for both Hindi and English).
 */
export function countWords(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

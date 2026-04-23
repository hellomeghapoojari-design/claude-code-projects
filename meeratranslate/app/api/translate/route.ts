import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/mongodb";
import Chapter from "@/models/Chapter";
import { translateChunk } from "@/lib/openai";
import { chunkText, getContextTail } from "@/utils/chunker";
import { Tone } from "@/types";

export const maxDuration = 300; // 5-minute timeout for long translations

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { text, tone, chapterId, bookId } = body as {
      text: string;
      tone: Tone;
      chapterId?: string;
      bookId?: string;
    };

    if (!text?.trim()) {
      return NextResponse.json({ error: "Text is required" }, { status: 400 });
    }
    if (!tone) {
      return NextResponse.json({ error: "Tone is required" }, { status: 400 });
    }

    // Split the full text into chunks of ~2500 words each
    const chunks = chunkText(text, 2500);
    const totalChunks = chunks.length;
    const translatedParts: string[] = [];

    for (let i = 0; i < chunks.length; i++) {
      // Pass the tail of the previous translated chunk as context
      // so the AI maintains smooth narrative flow across boundaries
      const previousContext =
        i > 0 ? getContextTail(translatedParts[i - 1], 150) : undefined;

      // Retry up to 2 times on transient API errors
      let translated = "";
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          translated = await translateChunk(
            chunks[i],
            tone,
            i,
            totalChunks,
            previousContext
          );
          break;
        } catch (err: any) {
          if (attempt === 2) throw err;
          // Wait 2s before retry
          await new Promise((r) => setTimeout(r, 2000));
        }
      }

      translatedParts.push(translated);
    }

    // Join translated chunks with a double newline between sections
    const fullTranslation = translatedParts.join("\n\n");

    // If a chapterId was passed, save the result to the DB automatically
    if (chapterId && bookId) {
      try {
        await connectDB();
        await Chapter.findOneAndUpdate(
          { _id: chapterId, bookId },
          { englishText: fullTranslation, status: "translated" }
        );
      } catch {
        // Non-fatal — still return the translation even if save fails
      }
    }

    return NextResponse.json({
      translatedText: fullTranslation,
      chunksProcessed: totalChunks,
      totalChunks,
    });
  } catch (err: any) {
    console.error("[translate]", err);
    return NextResponse.json(
      { error: err.message || "Translation failed" },
      { status: 500 }
    );
  }
}

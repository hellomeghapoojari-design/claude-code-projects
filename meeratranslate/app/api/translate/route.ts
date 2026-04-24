import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { translateChunk } from "@/lib/openai";
import { chunkText, getContextTail } from "@/utils/chunker";
import { Tone } from "@/types";

export const maxDuration = 300;

export async function POST(req: NextRequest) {
  if (!process.env.GROQ_API_KEY) {
    return NextResponse.json(
      { error: "GROQ_API_KEY is not set. Add it in your Railway Variables tab." },
      { status: 503 }
    );
  }

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

    const chunks = chunkText(text, 2500);
    const totalChunks = chunks.length;
    const translatedParts: string[] = [];

    for (let i = 0; i < chunks.length; i++) {
      const previousContext = i > 0 ? getContextTail(translatedParts[i - 1], 150) : undefined;
      let translated = "";
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          translated = await translateChunk(chunks[i], tone, i, totalChunks, previousContext);
          break;
        } catch (err: any) {
          if (attempt === 2) throw err;
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
      translatedParts.push(translated);
    }

    const fullTranslation = translatedParts.join("\n\n");

    if (chapterId && bookId) {
      try {
        const db = getDb();
        db.prepare(
          "UPDATE chapters SET english_text = ?, status = 'translated', updated_at = datetime('now') WHERE id = ? AND book_id = ?"
        ).run(fullTranslation, chapterId, bookId);
      } catch {
        // Non-fatal — still return the translation even if save fails
      }
    }

    return NextResponse.json({ translatedText: fullTranslation, chunksProcessed: totalChunks, totalChunks });
  } catch (err: any) {
    console.error("[translate]", err);
    return NextResponse.json({ error: err.message || "Translation failed" }, { status: 500 });
  }
}

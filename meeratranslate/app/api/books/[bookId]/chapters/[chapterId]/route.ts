import { NextRequest, NextResponse } from "next/server";
import { getDb, mapChapter } from "@/lib/db";
import { countWords } from "@/utils/chunker";

type Ctx = { params: { bookId: string; chapterId: string } };

export async function GET(_: NextRequest, { params }: Ctx) {
  try {
    const db = getDb();
    const row = db
      .prepare("SELECT * FROM chapters WHERE id = ? AND book_id = ?")
      .get(params.chapterId, params.bookId);
    if (!row) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(mapChapter(row));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function PUT(req: NextRequest, { params }: Ctx) {
  try {
    const body = await req.json();
    const db = getDb();

    const sets: string[] = ["updated_at = datetime('now')"];
    const vals: any[] = [];

    if (body.hindiText !== undefined) {
      sets.push("hindi_text = ?", "word_count = ?");
      vals.push(body.hindiText, countWords(body.hindiText));
    }
    if (body.englishText !== undefined) {
      sets.push("english_text = ?");
      vals.push(body.englishText);
      if (body.englishText.trim()) {
        sets.push("status = 'translated'");
      }
    }
    if (body.tone !== undefined) {
      sets.push("tone = ?");
      vals.push(body.tone);
    }
    if (body.title !== undefined) {
      sets.push("title = ?");
      vals.push(body.title);
    }

    vals.push(params.chapterId, params.bookId);
    db.prepare(
      `UPDATE chapters SET ${sets.join(", ")} WHERE id = ? AND book_id = ?`
    ).run(...vals);

    const row = db
      .prepare("SELECT * FROM chapters WHERE id = ? AND book_id = ?")
      .get(params.chapterId, params.bookId);
    if (!row) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(mapChapter(row));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE(_: NextRequest, { params }: Ctx) {
  try {
    const db = getDb();
    db.prepare("DELETE FROM chapters WHERE id = ? AND book_id = ?").run(
      params.chapterId,
      params.bookId
    );
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

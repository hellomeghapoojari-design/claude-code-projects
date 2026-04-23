import { NextRequest, NextResponse } from "next/server";
import { getDb, newId, mapChapter } from "@/lib/db";
import { countWords } from "@/utils/chunker";

type Ctx = { params: { bookId: string } };

export async function GET(_: NextRequest, { params }: Ctx) {
  try {
    const db = getDb();
    const rows = db
      .prepare("SELECT * FROM chapters WHERE book_id = ? ORDER BY order_index ASC")
      .all(params.bookId);
    return NextResponse.json(rows.map(mapChapter));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest, { params }: Ctx) {
  try {
    const { title, hindiText = "", tone = "thriller" } = await req.json();
    if (!title?.trim()) {
      return NextResponse.json({ error: "Chapter title is required" }, { status: 400 });
    }
    const db = getDb();
    const last = db
      .prepare("SELECT order_index FROM chapters WHERE book_id = ? ORDER BY order_index DESC LIMIT 1")
      .get(params.bookId) as any;
    const orderIndex = last ? last.order_index + 1 : 0;
    const id = newId();
    db.prepare(
      `INSERT INTO chapters (id, book_id, title, hindi_text, tone, order_index, word_count)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).run(id, params.bookId, title.trim(), hindiText, tone, orderIndex, countWords(hindiText));
    const row = db.prepare("SELECT * FROM chapters WHERE id = ?").get(id);
    return NextResponse.json(mapChapter(row), { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { getDb, mapBook } from "@/lib/db";

type Ctx = { params: { bookId: string } };

export async function GET(_: NextRequest, { params }: Ctx) {
  try {
    const db = getDb();
    const row = db.prepare("SELECT * FROM books WHERE id = ?").get(params.bookId);
    if (!row) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(mapBook(row));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function PUT(req: NextRequest, { params }: Ctx) {
  try {
    const { title, description, author } = await req.json();
    const db = getDb();
    db.prepare(
      `UPDATE books SET
        title       = COALESCE(?, title),
        description = COALESCE(?, description),
        author      = COALESCE(?, author),
        updated_at  = datetime('now')
       WHERE id = ?`
    ).run(title ?? null, description ?? null, author ?? null, params.bookId);
    const row = db.prepare("SELECT * FROM books WHERE id = ?").get(params.bookId);
    if (!row) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json(mapBook(row));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE(_: NextRequest, { params }: Ctx) {
  try {
    const db = getDb();
    db.prepare("DELETE FROM books WHERE id = ?").run(params.bookId);
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

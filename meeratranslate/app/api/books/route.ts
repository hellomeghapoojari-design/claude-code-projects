import { NextRequest, NextResponse } from "next/server";
import { getDb, newId, mapBook } from "@/lib/db";

export async function GET() {
  try {
    const db = getDb();
    const books = db.prepare("SELECT * FROM books ORDER BY created_at DESC").all();
    const countStmt = db.prepare("SELECT COUNT(*) as n FROM chapters WHERE book_id = ?");
    const result = books.map((b: any) => {
      const { n } = countStmt.get(b.id) as any;
      return mapBook(b, n);
    });
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const { title, description = "", author = "" } = await req.json();
    if (!title?.trim()) {
      return NextResponse.json({ error: "Title is required" }, { status: 400 });
    }
    const db = getDb();
    const id = newId();
    db.prepare(
      "INSERT INTO books (id, title, description, author) VALUES (?, ?, ?, ?)"
    ).run(id, title.trim(), description, author);
    const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
    return NextResponse.json(mapBook(row), { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

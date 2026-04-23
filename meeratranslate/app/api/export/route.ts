import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const bookId = searchParams.get("bookId");
    const chapterId = searchParams.get("chapterId");
    const format = searchParams.get("format") ?? "txt";

    if (!bookId) {
      return NextResponse.json({ error: "bookId is required" }, { status: 400 });
    }

    const db = getDb();
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(bookId) as any;
    if (!book) return NextResponse.json({ error: "Book not found" }, { status: 404 });

    const chapters: any[] = chapterId
      ? db
          .prepare("SELECT * FROM chapters WHERE id = ? AND book_id = ? ORDER BY order_index ASC")
          .all(chapterId, bookId)
      : db
          .prepare("SELECT * FROM chapters WHERE book_id = ? ORDER BY order_index ASC")
          .all(bookId);

    if (!chapters.length) {
      return NextResponse.json({ error: "No chapters found" }, { status: 404 });
    }

    const bookTitle = book.title as string;
    const textContent = chapters
      .map((ch) => `=== ${ch.title} ===\n\n${ch.english_text || "[Not yet translated]"}`)
      .join("\n\n\n");

    if (format === "txt") {
      return new NextResponse(textContent, {
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "Content-Disposition": `attachment; filename="${bookTitle}.txt"`,
        },
      });
    }

    if (format === "docx") {
      const { Document, Packer, Paragraph, TextRun, HeadingLevel } = await import("docx");
      const docChildren: any[] = [
        new Paragraph({ text: bookTitle, heading: HeadingLevel.TITLE }),
        new Paragraph({ text: "" }),
      ];
      for (const ch of chapters) {
        docChildren.push(
          new Paragraph({ text: ch.title, heading: HeadingLevel.HEADING_1 }),
          new Paragraph({ text: "" })
        );
        for (const line of (ch.english_text || "[Not yet translated]").split("\n")) {
          docChildren.push(
            new Paragraph({
              children: [new TextRun({ text: line, size: 24 })],
              spacing: { after: 200 },
            })
          );
        }
        docChildren.push(new Paragraph({ text: "" }));
      }
      const buffer = await Packer.toBuffer(new Document({ sections: [{ children: docChildren }] }));
      return new NextResponse(buffer, {
        headers: {
          "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "Content-Disposition": `attachment; filename="${bookTitle}.docx"`,
        },
      });
    }

    if (format === "pdf") {
      return NextResponse.json({ content: textContent, title: bookTitle });
    }

    return NextResponse.json({ error: "Unsupported format" }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/mongodb";
import Chapter from "@/models/Chapter";
import Book from "@/models/Book";

// GET /api/export?bookId=xxx&chapterId=yyy&format=docx|txt|pdf
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const bookId = searchParams.get("bookId");
    const chapterId = searchParams.get("chapterId");
    const format = searchParams.get("format") ?? "txt";

    if (!bookId) {
      return NextResponse.json({ error: "bookId is required" }, { status: 400 });
    }

    await connectDB();

    const book = await Book.findById(bookId).lean();
    if (!book) return NextResponse.json({ error: "Book not found" }, { status: 404 });

    // Fetch chapters (single or all)
    const chapters = chapterId
      ? await Chapter.find({ _id: chapterId, bookId }).sort({ orderIndex: 1 }).lean()
      : await Chapter.find({ bookId }).sort({ orderIndex: 1 }).lean();

    if (!chapters.length) {
      return NextResponse.json({ error: "No chapters found" }, { status: 404 });
    }

    const bookTitle = (book as any).title as string;

    // Build plain text content
    const textContent = chapters
      .map((ch) => `=== ${ch.title} ===\n\n${ch.englishText || "[Not yet translated]"}`)
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
      // Dynamically import to keep bundle size small
      const { Document, Packer, Paragraph, TextRun, HeadingLevel } = await import("docx");

      const docChildren: any[] = [
        new Paragraph({
          text: bookTitle,
          heading: HeadingLevel.TITLE,
        }),
        new Paragraph({ text: "" }),
      ];

      for (const ch of chapters) {
        docChildren.push(
          new Paragraph({ text: ch.title, heading: HeadingLevel.HEADING_1 }),
          new Paragraph({ text: "" })
        );

        const lines = (ch.englishText || "[Not yet translated]").split("\n");
        for (const line of lines) {
          docChildren.push(
            new Paragraph({
              children: [new TextRun({ text: line, size: 24 })],
              spacing: { after: 200 },
            })
          );
        }
        docChildren.push(new Paragraph({ text: "" }));
      }

      const doc = new Document({ sections: [{ children: docChildren }] });
      const buffer = await Packer.toBuffer(doc);

      return new NextResponse(buffer, {
        headers: {
          "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "Content-Disposition": `attachment; filename="${bookTitle}.docx"`,
        },
      });
    }

    if (format === "pdf") {
      // We return plain text for PDF — the client uses jsPDF to render
      // This avoids server-side canvas dependencies
      return NextResponse.json({ content: textContent, title: bookTitle });
    }

    return NextResponse.json({ error: "Unsupported format" }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

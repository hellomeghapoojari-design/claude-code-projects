import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/mongodb";
import Chapter from "@/models/Chapter";
import { countWords } from "@/utils/chunker";

// GET /api/books/:bookId/chapters
export async function GET(_: NextRequest, { params }: { params: { bookId: string } }) {
  try {
    await connectDB();
    const chapters = await Chapter.find({ bookId: params.bookId })
      .sort({ orderIndex: 1 })
      .lean();
    return NextResponse.json(
      chapters.map((c) => ({ ...c, _id: c._id.toString(), bookId: c.bookId.toString() }))
    );
  } catch {
    return NextResponse.json({ error: "Failed to fetch chapters" }, { status: 500 });
  }
}

// POST /api/books/:bookId/chapters
export async function POST(req: NextRequest, { params }: { params: { bookId: string } }) {
  try {
    await connectDB();
    const body = await req.json();
    const { title, hindiText = "", tone = "thriller" } = body;

    if (!title?.trim()) {
      return NextResponse.json({ error: "Chapter title is required" }, { status: 400 });
    }

    // Auto-assign orderIndex as next in sequence
    const lastChapter = await Chapter.findOne({ bookId: params.bookId }).sort({ orderIndex: -1 });
    const orderIndex = lastChapter ? lastChapter.orderIndex + 1 : 0;

    const chapter = await Chapter.create({
      bookId: params.bookId,
      title: title.trim(),
      hindiText,
      tone,
      orderIndex,
      wordCount: countWords(hindiText),
    });

    return NextResponse.json(
      { ...chapter.toObject(), _id: chapter._id.toString(), bookId: params.bookId },
      { status: 201 }
    );
  } catch {
    return NextResponse.json({ error: "Failed to create chapter" }, { status: 500 });
  }
}

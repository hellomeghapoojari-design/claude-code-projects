import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/mongodb";
import Chapter from "@/models/Chapter";
import { countWords } from "@/utils/chunker";

type Ctx = { params: { bookId: string; chapterId: string } };

// GET /api/books/:bookId/chapters/:chapterId
export async function GET(_: NextRequest, { params }: Ctx) {
  try {
    await connectDB();
    const chapter = await Chapter.findOne({ _id: params.chapterId, bookId: params.bookId }).lean();
    if (!chapter) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ ...chapter, _id: chapter._id.toString(), bookId: chapter.bookId.toString() });
  } catch {
    return NextResponse.json({ error: "Failed to fetch chapter" }, { status: 500 });
  }
}

// PUT /api/books/:bookId/chapters/:chapterId — auto-save + tone/text updates
export async function PUT(req: NextRequest, { params }: Ctx) {
  try {
    await connectDB();
    const body = await req.json();

    // Recalculate word count if hindiText changed
    if (body.hindiText !== undefined) {
      body.wordCount = countWords(body.hindiText);
    }

    // Mark as translated if english text is provided
    if (body.englishText && body.englishText.trim()) {
      body.status = "translated";
    }

    const chapter = await Chapter.findOneAndUpdate(
      { _id: params.chapterId, bookId: params.bookId },
      body,
      { new: true }
    ).lean();

    if (!chapter) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ ...chapter, _id: chapter._id.toString(), bookId: chapter.bookId.toString() });
  } catch {
    return NextResponse.json({ error: "Failed to update chapter" }, { status: 500 });
  }
}

// DELETE /api/books/:bookId/chapters/:chapterId
export async function DELETE(_: NextRequest, { params }: Ctx) {
  try {
    await connectDB();
    await Chapter.findOneAndDelete({ _id: params.chapterId, bookId: params.bookId });
    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json({ error: "Failed to delete chapter" }, { status: 500 });
  }
}

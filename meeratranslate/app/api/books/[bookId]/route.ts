import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/mongodb";
import Book from "@/models/Book";
import Chapter from "@/models/Chapter";

// GET /api/books/:id
export async function GET(_: NextRequest, { params }: { params: { bookId: string } }) {
  try {
    await connectDB();
    const book = await Book.findById(params.bookId).lean();
    if (!book) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ ...book, _id: book._id.toString() });
  } catch {
    return NextResponse.json({ error: "Failed to fetch book" }, { status: 500 });
  }
}

// PUT /api/books/:id
export async function PUT(req: NextRequest, { params }: { params: { bookId: string } }) {
  try {
    await connectDB();
    const body = await req.json();
    const book = await Book.findByIdAndUpdate(params.bookId, body, { new: true }).lean();
    if (!book) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ ...book, _id: book._id.toString() });
  } catch {
    return NextResponse.json({ error: "Failed to update book" }, { status: 500 });
  }
}

// DELETE /api/books/:id — also deletes all chapters
export async function DELETE(_: NextRequest, { params }: { params: { bookId: string } }) {
  try {
    await connectDB();
    await Book.findByIdAndDelete(params.bookId);
    await Chapter.deleteMany({ bookId: params.bookId });
    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json({ error: "Failed to delete book" }, { status: 500 });
  }
}

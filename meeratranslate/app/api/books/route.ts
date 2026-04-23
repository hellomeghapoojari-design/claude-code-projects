import { NextRequest, NextResponse } from "next/server";
import { connectDB } from "@/lib/mongodb";
import Book from "@/models/Book";
import Chapter from "@/models/Chapter";

// GET /api/books — list all books with chapter counts
export async function GET() {
  try {
    await connectDB();
    const books = await Book.find().sort({ createdAt: -1 }).lean();

    // Attach chapter count to each book
    const booksWithCount = await Promise.all(
      books.map(async (book) => ({
        ...book,
        _id: book._id.toString(),
        chapterCount: await Chapter.countDocuments({ bookId: book._id }),
      }))
    );

    return NextResponse.json(booksWithCount);
  } catch (err) {
    return NextResponse.json({ error: "Failed to fetch books" }, { status: 500 });
  }
}

// POST /api/books — create a new book
export async function POST(req: NextRequest) {
  try {
    await connectDB();
    const body = await req.json();
    const { title, description, author } = body;

    if (!title?.trim()) {
      return NextResponse.json({ error: "Title is required" }, { status: 400 });
    }

    const book = await Book.create({ title: title.trim(), description, author });
    return NextResponse.json({ ...book.toObject(), _id: book._id.toString() }, { status: 201 });
  } catch (err) {
    return NextResponse.json({ error: "Failed to create book" }, { status: 500 });
  }
}

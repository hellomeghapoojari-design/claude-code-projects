import { NextRequest, NextResponse } from "next/server";

// POST /api/upload — accepts .txt or .docx, returns extracted plain text
export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const fileName = file.name.toLowerCase();
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    if (fileName.endsWith(".txt")) {
      const text = buffer.toString("utf-8");
      return NextResponse.json({ text });
    }

    if (fileName.endsWith(".docx")) {
      // mammoth extracts raw text from .docx preserving paragraph structure
      const mammoth = await import("mammoth");
      const result = await mammoth.extractRawText({ buffer });
      return NextResponse.json({ text: result.value });
    }

    return NextResponse.json(
      { error: "Unsupported file type. Please upload .txt or .docx" },
      { status: 400 }
    );
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

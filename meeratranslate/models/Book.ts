import mongoose, { Schema, Document, Model } from "mongoose";

export interface IBookDocument extends Document {
  title: string;
  description: string;
  author: string;
  createdAt: Date;
  updatedAt: Date;
}

const BookSchema = new Schema<IBookDocument>(
  {
    title: { type: String, required: true, trim: true },
    description: { type: String, default: "" },
    author: { type: String, default: "Unknown Author" },
  },
  { timestamps: true }
);

// Prevent model re-compilation in Next.js hot reload
const Book: Model<IBookDocument> =
  mongoose.models.Book || mongoose.model<IBookDocument>("Book", BookSchema);

export default Book;

import mongoose, { Schema, Document, Model } from "mongoose";
import { Tone } from "@/types";

export interface IChapterDocument extends Document {
  bookId: mongoose.Types.ObjectId;
  title: string;
  orderIndex: number;
  hindiText: string;
  englishText: string;
  tone: Tone;
  status: "untranslated" | "translating" | "translated";
  wordCount: number;
  createdAt: Date;
  updatedAt: Date;
}

const ChapterSchema = new Schema<IChapterDocument>(
  {
    bookId: { type: Schema.Types.ObjectId, ref: "Book", required: true, index: true },
    title: { type: String, required: true, trim: true },
    orderIndex: { type: Number, default: 0 },
    hindiText: { type: String, default: "" },
    englishText: { type: String, default: "" },
    tone: {
      type: String,
      enum: ["eerie", "haunting", "thriller", "suspense"],
      default: "thriller",
    },
    status: {
      type: String,
      enum: ["untranslated", "translating", "translated"],
      default: "untranslated",
    },
    wordCount: { type: Number, default: 0 },
  },
  { timestamps: true }
);

const Chapter: Model<IChapterDocument> =
  mongoose.models.Chapter ||
  mongoose.model<IChapterDocument>("Chapter", ChapterSchema);

export default Chapter;

export type Tone = "eerie" | "haunting" | "thriller" | "suspense";

export interface IBook {
  _id: string;
  title: string;
  description: string;
  author: string;
  createdAt: string;
  updatedAt: string;
  chapterCount?: number;
}

export interface IChapter {
  _id: string;
  bookId: string;
  title: string;
  orderIndex: number;
  hindiText: string;
  englishText: string;
  tone: Tone;
  status: "untranslated" | "translating" | "translated";
  wordCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface TranslateRequest {
  text: string;
  tone: Tone;
  chapterId?: string;
}

export interface TranslateResponse {
  translatedText: string;
  chunksProcessed: number;
  totalChunks: number;
}

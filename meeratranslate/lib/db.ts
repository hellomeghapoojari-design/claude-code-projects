import Database from "better-sqlite3";
import { randomUUID } from "crypto";
import path from "path";

const DB_PATH =
  process.env.NODE_ENV === "production"
    ? "/tmp/meeratranslate.db"
    : path.join(process.cwd(), "dev.db");

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (_db) return _db;
  const cached = (global as any).__sqlite as Database.Database | undefined;
  if (cached) return (_db = cached);

  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id          TEXT PRIMARY KEY,
      title       TEXT NOT NULL,
      description TEXT DEFAULT '',
      author      TEXT DEFAULT '',
      created_at  TEXT DEFAULT (datetime('now')),
      updated_at  TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS chapters (
      id           TEXT PRIMARY KEY,
      book_id      TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
      title        TEXT NOT NULL,
      hindi_text   TEXT DEFAULT '',
      english_text TEXT DEFAULT '',
      tone         TEXT DEFAULT 'thriller',
      order_index  INTEGER DEFAULT 0,
      word_count   INTEGER DEFAULT 0,
      status       TEXT DEFAULT 'untranslated',
      created_at   TEXT DEFAULT (datetime('now')),
      updated_at   TEXT DEFAULT (datetime('now'))
    );
  `);

  (global as any).__sqlite = db;
  _db = db;
  return db;
}

export function newId(): string {
  return randomUUID();
}

export function mapBook(row: any, chapterCount = 0) {
  return {
    _id: row.id,
    title: row.title,
    description: row.description ?? "",
    author: row.author ?? "",
    chapterCount,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function mapChapter(row: any) {
  return {
    _id: row.id,
    bookId: row.book_id,
    title: row.title,
    hindiText: row.hindi_text ?? "",
    englishText: row.english_text ?? "",
    tone: row.tone ?? "thriller",
    orderIndex: row.order_index ?? 0,
    wordCount: row.word_count ?? 0,
    status: row.status ?? "untranslated",
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

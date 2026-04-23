"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, Plus, Trash2, BookMarked } from "lucide-react";
import { IBook } from "@/types";

export default function BooksPage() {
  const [books, setBooks] = useState<IBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", author: "" });

  async function fetchBooks() {
    const res = await fetch("/api/books");
    const data = await res.json();
    setBooks(data);
    setLoading(false);
  }

  useEffect(() => { fetchBooks(); }, []);

  async function createBook(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setCreating(true);
    await fetch("/api/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setForm({ title: "", description: "", author: "" });
    setShowForm(false);
    setCreating(false);
    fetchBooks();
  }

  async function deleteBook(id: string) {
    if (!confirm("Delete this book and all its chapters?")) return;
    await fetch(`/api/books/${id}`, { method: "DELETE" });
    setBooks((prev) => prev.filter((b) => b._id !== id));
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <nav className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookMarked className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold tracking-tight">MeeraTranslate</span>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Plus className="h-4 w-4" /> New Book
        </button>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Your Books</h1>
          <p className="text-muted-foreground">Manage your Hindi manuscripts and their translations.</p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-44 bg-card rounded-xl animate-pulse border border-border" />
            ))}
          </div>
        ) : books.length === 0 ? (
          <div className="text-center py-24 border border-dashed border-border rounded-xl">
            <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground text-lg">No books yet.</p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 text-primary hover:underline text-sm"
            >
              Create your first book →
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {books.map((book) => (
              <div
                key={book._id}
                className="bg-card border border-border rounded-xl p-6 flex flex-col justify-between hover:border-primary/50 transition-colors group"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <Link
                      href={`/books/${book._id}`}
                      className="text-lg font-semibold leading-tight hover:text-primary transition-colors"
                    >
                      {book.title}
                    </Link>
                    <button
                      onClick={() => deleteBook(book._id)}
                      className="text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  {book.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                      {book.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-between mt-4">
                  <span className="text-xs text-muted-foreground">
                    {book.author || "Unknown Author"}
                  </span>
                  <span className="text-xs bg-accent text-accent-foreground px-2.5 py-1 rounded-full">
                    {book.chapterCount ?? 0} chapter{book.chapterCount !== 1 ? "s" : ""}
                  </span>
                </div>
                <Link
                  href={`/books/${book._id}`}
                  className="mt-4 text-sm text-primary hover:underline"
                >
                  Open Book →
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Book Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-5">Create New Book</h2>
            <form onSubmit={createBook} className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground mb-1.5 block">
                  Book Title *
                </label>
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Andhere Ki Awaaz"
                  className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-1 focus:ring-primary"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground mb-1.5 block">Author Name</label>
                <input
                  value={form.author}
                  onChange={(e) => setForm({ ...form, author: e.target.value })}
                  placeholder="Your name"
                  className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground mb-1.5 block">
                  Description (optional)
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Brief synopsis of your book…"
                  rows={3}
                  className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 bg-secondary text-secondary-foreground py-2.5 rounded-lg text-sm font-medium hover:opacity-80 transition-opacity"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 bg-primary text-primary-foreground py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {creating ? "Creating…" : "Create Book"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

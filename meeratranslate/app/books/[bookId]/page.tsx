"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  BookMarked, Plus, Trash2, CheckCircle2, Clock, ChevronRight, ArrowLeft,
} from "lucide-react";
import { IBook, IChapter, Tone } from "@/types";

const STATUS_CONFIG = {
  translated:   { label: "Translated",   icon: CheckCircle2, cls: "text-emerald-400" },
  translating:  { label: "In Progress",  icon: Clock,        cls: "text-amber-400" },
  untranslated: { label: "Not Started",  icon: Clock,        cls: "text-muted-foreground" },
};

const TONES: { value: Tone; label: string }[] = [
  { value: "thriller",  label: "Thriller" },
  { value: "suspense",  label: "Suspense" },
  { value: "eerie",     label: "Eerie" },
  { value: "haunting",  label: "Haunting" },
];

export default function BookPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const router = useRouter();
  const [book, setBook]       = useState<IBook | null>(null);
  const [chapters, setChapters] = useState<IChapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm]       = useState({ title: "", tone: "thriller" as Tone });
  const [creating, setCreating] = useState(false);

  async function fetchData() {
    const [bookRes, chapRes] = await Promise.all([
      fetch(`/api/books/${bookId}`),
      fetch(`/api/books/${bookId}/chapters`),
    ]);
    setBook(await bookRes.json());
    setChapters(await chapRes.json());
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, [bookId]);

  async function createChapter(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setCreating(true);
    await fetch(`/api/books/${bookId}/chapters`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setForm({ title: "", tone: "thriller" });
    setShowForm(false);
    setCreating(false);
    fetchData();
  }

  async function deleteChapter(chapterId: string) {
    if (!confirm("Delete this chapter?")) return;
    await fetch(`/api/books/${bookId}/chapters/${chapterId}`, { method: "DELETE" });
    setChapters((prev) => prev.filter((c) => c._id !== chapterId));
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground">Loading…</div>
      </div>
    );
  }

  if (!book) return null;

  const translatedCount = chapters.filter((c) => c.status === "translated").length;

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <nav className="border-b border-border px-6 py-4 flex items-center gap-4">
        <Link href="/books" className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <BookMarked className="h-5 w-5 text-primary" />
        <span className="font-semibold">{book.title}</span>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-10">
        {/* Book header */}
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold mb-1">{book.title}</h1>
            {book.author && <p className="text-muted-foreground text-sm">by {book.author}</p>}
            {book.description && (
              <p className="text-muted-foreground mt-2 text-sm max-w-xl">{book.description}</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-2xl font-bold text-primary">{translatedCount}/{chapters.length}</p>
            <p className="text-xs text-muted-foreground">chapters translated</p>
          </div>
        </div>

        {/* Chapter list */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold">Chapters</h2>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 text-sm bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90 transition-opacity font-medium"
          >
            <Plus className="h-4 w-4" /> Add Chapter
          </button>
        </div>

        {chapters.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-border rounded-xl">
            <p className="text-muted-foreground">No chapters yet.</p>
            <button onClick={() => setShowForm(true)} className="mt-3 text-primary text-sm hover:underline">
              Add your first chapter →
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {chapters.map((ch, idx) => {
              const cfg = STATUS_CONFIG[ch.status];
              const Icon = cfg.icon;
              return (
                <div
                  key={ch._id}
                  className="bg-card border border-border rounded-xl px-5 py-4 flex items-center justify-between gap-4 hover:border-primary/40 transition-colors group"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <span className="text-muted-foreground text-sm font-mono w-6 shrink-0">
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{ch.title}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className={`flex items-center gap-1 text-xs ${cfg.cls}`}>
                          <Icon className="h-3 w-3" /> {cfg.label}
                        </span>
                        <span className={`text-xs border px-2 py-0.5 rounded-full tone-${ch.tone}`}>
                          {ch.tone}
                        </span>
                        {ch.wordCount > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {ch.wordCount.toLocaleString()} words
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      onClick={() => deleteChapter(ch._id)}
                      className="text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <Link
                      href={`/books/${bookId}/chapters/${ch._id}`}
                      className="flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      {ch.status === "translated" ? "Edit" : "Translate"} <ChevronRight className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Add Chapter Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-sm p-6">
            <h2 className="text-xl font-bold mb-5">Add Chapter</h2>
            <form onSubmit={createChapter} className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground mb-1.5 block">Chapter Title *</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Chapter 1 — The Beginning"
                  className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-1 focus:ring-primary"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground mb-1.5 block">Default Tone</label>
                <select
                  value={form.tone}
                  onChange={(e) => setForm({ ...form, tone: e.target.value as Tone })}
                  className="w-full bg-input border border-border rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-1 focus:ring-primary"
                >
                  {TONES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 bg-secondary text-secondary-foreground py-2.5 rounded-lg text-sm font-medium hover:opacity-80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 bg-primary text-primary-foreground py-2.5 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {creating ? "Creating…" : "Add Chapter"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

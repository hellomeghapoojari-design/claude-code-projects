"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Wand2, Save, Upload, Download, BookMarked,
  Loader2, CheckCircle2, AlertCircle,
} from "lucide-react";
import { IChapter, Tone } from "@/types";

const TONES: { value: Tone; label: string; description: string }[] = [
  { value: "thriller",  label: "Thriller",  description: "Fast-paced, gripping tension" },
  { value: "suspense",  label: "Suspense",  description: "Slow dread, creeping unease" },
  { value: "eerie",     label: "Eerie",     description: "Quiet, unsettling wrongness" },
  { value: "haunting",  label: "Haunting",  description: "Melancholic, lingering sorrow" },
];

type SaveState = "idle" | "saving" | "saved" | "error";
type TranslateState = "idle" | "loading" | "done" | "error";

export default function ChapterEditorPage() {
  const { bookId, chapterId } = useParams<{ bookId: string; chapterId: string }>();

  const [chapter, setChapter] = useState<IChapter | null>(null);
  const [hindiText, setHindiText]   = useState("");
  const [englishText, setEnglishText] = useState("");
  const [tone, setTone]             = useState<Tone>("thriller");
  const [saveState, setSaveState]   = useState<SaveState>("idle");
  const [translateState, setTranslateState] = useState<TranslateState>("idle");
  const [progress, setProgress]     = useState({ current: 0, total: 0 });
  const [errorMsg, setErrorMsg]     = useState("");
  const autoSaveTimer               = useRef<NodeJS.Timeout | null>(null);

  // Fetch chapter on mount
  useEffect(() => {
    fetch(`/api/books/${bookId}/chapters/${chapterId}`)
      .then((r) => r.json())
      .then((data: IChapter) => {
        setChapter(data);
        setHindiText(data.hindiText || "");
        setEnglishText(data.englishText || "");
        setTone(data.tone || "thriller");
      });
  }, [bookId, chapterId]);

  // Auto-save after 2 seconds of inactivity
  const triggerAutoSave = useCallback(
    (newHindi: string, newEnglish: string, newTone: Tone) => {
      if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
      autoSaveTimer.current = setTimeout(async () => {
        setSaveState("saving");
        try {
          await fetch(`/api/books/${bookId}/chapters/${chapterId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ hindiText: newHindi, englishText: newEnglish, tone: newTone }),
          });
          setSaveState("saved");
          setTimeout(() => setSaveState("idle"), 2000);
        } catch {
          setSaveState("error");
        }
      }, 2000);
    },
    [bookId, chapterId]
  );

  function handleHindiChange(val: string) {
    setHindiText(val);
    triggerAutoSave(val, englishText, tone);
  }

  function handleEnglishChange(val: string) {
    setEnglishText(val);
    triggerAutoSave(hindiText, val, tone);
  }

  function handleToneChange(newTone: Tone) {
    setTone(newTone);
    triggerAutoSave(hindiText, englishText, newTone);
  }

  // Manual save
  async function saveNow() {
    setSaveState("saving");
    await fetch(`/api/books/${bookId}/chapters/${chapterId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hindiText, englishText, tone }),
    });
    setSaveState("saved");
    setTimeout(() => setSaveState("idle"), 2000);
  }

  // Translate using AI (streaming progress via chunks)
  async function translate() {
    if (!hindiText.trim()) return;
    setTranslateState("loading");
    setErrorMsg("");
    setProgress({ current: 0, total: 0 });

    try {
      const res = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: hindiText, tone, chapterId, bookId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Translation failed");
      }

      const data = await res.json();
      setEnglishText(data.translatedText);
      setProgress({ current: data.chunksProcessed, total: data.totalChunks });
      setTranslateState("done");
      setTimeout(() => setTranslateState("idle"), 3000);
    } catch (err: any) {
      setErrorMsg(err.message);
      setTranslateState("error");
      setTimeout(() => setTranslateState("idle"), 5000);
    }
  }

  // Upload .txt or .docx file into Hindi pane
  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const data = await res.json();
    if (data.text) {
      setHindiText(data.text);
      triggerAutoSave(data.text, englishText, tone);
    }
    e.target.value = ""; // reset input
  }

  // Export translated text
  async function exportChapter(format: "txt" | "docx" | "pdf") {
    if (format === "pdf") {
      // Client-side PDF via jsPDF
      const { jsPDF } = await import("jspdf");
      const doc = new jsPDF();
      const lines = doc.splitTextToSize(englishText, 180);
      let y = 15;
      doc.setFontSize(16);
      doc.text(chapter?.title ?? "Chapter", 15, y);
      y += 10;
      doc.setFontSize(12);
      lines.forEach((line: string) => {
        if (y > 280) { doc.addPage(); y = 15; }
        doc.text(line, 15, y);
        y += 7;
      });
      doc.save(`${chapter?.title ?? "chapter"}.pdf`);
      return;
    }

    const url = `/api/export?bookId=${bookId}&chapterId=${chapterId}&format=${format}`;
    window.open(url, "_blank");
  }

  if (!chapter) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Top Navbar */}
      <header className="border-b border-border px-5 py-3 flex items-center gap-4 shrink-0">
        <Link href={`/books/${bookId}`} className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <BookMarked className="h-5 w-5 text-primary" />
        <span className="font-semibold truncate flex-1">{chapter.title}</span>

        {/* Save indicator */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {saveState === "saving" && <><Loader2 className="h-3 w-3 animate-spin" /> Saving…</>}
          {saveState === "saved"  && <><CheckCircle2 className="h-3 w-3 text-emerald-400" /> Saved</>}
          {saveState === "error"  && <><AlertCircle className="h-3 w-3 text-red-400" /> Save failed</>}
        </div>

        {/* Action buttons */}
        <button onClick={saveNow} className="flex items-center gap-1.5 text-xs bg-secondary text-secondary-foreground px-3 py-1.5 rounded-lg hover:opacity-80 transition-opacity">
          <Save className="h-3.5 w-3.5" /> Save
        </button>

        <label className="flex items-center gap-1.5 text-xs bg-secondary text-secondary-foreground px-3 py-1.5 rounded-lg hover:opacity-80 transition-opacity cursor-pointer">
          <Upload className="h-3.5 w-3.5" /> Upload
          <input type="file" accept=".txt,.docx" onChange={handleFileUpload} className="hidden" />
        </label>

        {/* Export dropdown */}
        <div className="relative group">
          <button className="flex items-center gap-1.5 text-xs bg-secondary text-secondary-foreground px-3 py-1.5 rounded-lg hover:opacity-80 transition-opacity">
            <Download className="h-3.5 w-3.5" /> Export
          </button>
          <div className="absolute right-0 top-full mt-1 bg-card border border-border rounded-lg overflow-hidden shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-20 min-w-[120px]">
            {(["txt", "docx", "pdf"] as const).map((fmt) => (
              <button key={fmt} onClick={() => exportChapter(fmt)}
                className="block w-full text-left px-4 py-2 text-xs hover:bg-accent hover:text-accent-foreground transition-colors uppercase tracking-wide">
                .{fmt}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Tone Selector */}
      <div className="border-b border-border px-5 py-2.5 flex items-center gap-3 shrink-0 overflow-x-auto">
        <span className="text-xs text-muted-foreground shrink-0 font-medium">Tone:</span>
        {TONES.map((t) => (
          <button
            key={t.value}
            onClick={() => handleToneChange(t.value)}
            title={t.description}
            className={`text-xs px-3 py-1.5 rounded-full border transition-all shrink-0 font-medium tone-${t.value} ${
              tone === t.value
                ? "ring-1 ring-primary opacity-100"
                : "opacity-40 hover:opacity-70"
            }`}
          >
            {t.label}
          </button>
        ))}

        {/* Translate button */}
        <div className="ml-auto shrink-0 flex items-center gap-3">
          {translateState === "loading" && progress.total > 0 && (
            <span className="text-xs text-muted-foreground">
              Chunk {progress.current}/{progress.total}…
            </span>
          )}
          {translateState === "error" && (
            <span className="text-xs text-red-400 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" /> {errorMsg}
            </span>
          )}
          <button
            onClick={translate}
            disabled={translateState === "loading" || !hindiText.trim()}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-1.5 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {translateState === "loading" ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Translating…</>
            ) : (
              <><Wand2 className="h-4 w-4" /> Translate</>
            )}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {translateState === "loading" && (
        <div className="h-0.5 bg-border">
          <div className="h-full bg-primary animate-pulse" style={{ width: "100%" }} />
        </div>
      )}

      {/* Split Editor */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Hindi Input */}
        <div className="flex-1 flex flex-col border-r border-border overflow-hidden">
          <div className="px-4 py-2 border-b border-border bg-card/50 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Hindi Input
            </span>
            <span className="text-xs text-muted-foreground">
              {hindiText.trim() ? hindiText.trim().split(/\s+/).length.toLocaleString() : 0} words
            </span>
          </div>
          <textarea
            value={hindiText}
            onChange={(e) => handleHindiChange(e.target.value)}
            placeholder="Paste your Hindi text here, or upload a .txt / .docx file using the Upload button above…"
            className="flex-1 bg-transparent px-6 py-5 writing-area outline-none text-foreground placeholder:text-muted-foreground/40 overflow-y-auto"
            spellCheck={false}
          />
        </div>

        {/* Right: English Output */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-4 py-2 border-b border-border bg-card/50 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              English Translation
            </span>
            <div className="flex items-center gap-2">
              {translateState === "done" && (
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Translation complete
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {englishText.trim() ? englishText.trim().split(/\s+/).length.toLocaleString() : 0} words
              </span>
            </div>
          </div>
          <textarea
            value={englishText}
            onChange={(e) => handleEnglishChange(e.target.value)}
            placeholder="Translated English text will appear here. You can also edit it directly."
            className="flex-1 bg-transparent px-6 py-5 writing-area outline-none text-foreground placeholder:text-muted-foreground/40 overflow-y-auto"
          />
        </div>
      </div>
    </div>
  );
}

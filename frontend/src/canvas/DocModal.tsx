import {
  Bold, Eye, Heading, Italic, List, ListOrdered, Link as LinkIcon, Pencil, Redo2, Underline, X,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api } from "../lib/api";

// Shared prose styling for both the editor surface and the read-only preview.
const PROSE =
  "[&_h3]:mb-1 [&_h3]:mt-2 [&_h3]:text-base [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 " +
  "[&_ol]:list-decimal [&_ol]:pl-5 [&_a]:text-[hsl(var(--accent))] [&_a]:underline";

// Minimal WYSIWYG built on contentEditable + execCommand — no external dependency
// (keeps the bundle small and avoids the corporate npm proxy). Stores HTML.
function RichTextEditor({ initial, onChange }: { initial: string; onChange: (html: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  // Freeze the initial HTML at mount so React never re-applies it on re-render;
  // otherwise dangerouslySetInnerHTML resets the caret to the start on each
  // keystroke and text comes out reversed.
  const frozen = useRef(initial);

  function exec(cmd: string, arg?: string) {
    ref.current?.focus();
    document.execCommand(cmd, false, arg);
    onChange(ref.current?.innerHTML ?? "");
  }

  const Btn = ({ cmd, arg, title, children }: { cmd: string; arg?: string; title: string; children: ReactNode }) => (
    <button type="button" title={title} className="rounded p-1.5 hover:bg-black/10 dark:hover:bg-white/10"
      onMouseDown={(e) => e.preventDefault()} onClick={() => exec(cmd, arg)}>
      {children}
    </button>
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-0.5 border-b px-2 py-1">
        <Btn cmd="bold" title="Negrita"><Bold size={15} /></Btn>
        <Btn cmd="italic" title="Cursiva"><Italic size={15} /></Btn>
        <Btn cmd="underline" title="Subrayado"><Underline size={15} /></Btn>
        <span className="mx-1 h-4 w-px bg-black/15" />
        <Btn cmd="formatBlock" arg="<h3>" title="Título"><Heading size={15} /></Btn>
        <Btn cmd="insertUnorderedList" title="Lista"><List size={15} /></Btn>
        <Btn cmd="insertOrderedList" title="Lista numerada"><ListOrdered size={15} /></Btn>
        <button type="button" title="Enlace" className="rounded p-1.5 hover:bg-black/10 dark:hover:bg-white/10"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => { const url = window.prompt("URL del enlace:"); if (url) exec("createLink", url); }}>
          <LinkIcon size={15} />
        </button>
        <Btn cmd="removeFormat" title="Quitar formato"><Redo2 size={15} /></Btn>
      </div>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        className={`min-h-48 flex-1 overflow-auto p-3 text-sm focus:outline-none ${PROSE}`}
        dangerouslySetInnerHTML={{ __html: frozen.current }}
        onInput={(e) => onChange(e.currentTarget.innerHTML)}
      />
    </div>
  );
}

// Read-only render where links are clickable (open in a new, safe tab).
function Preview({ html }: { html: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelectorAll("a").forEach((a) => {
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener noreferrer");
    });
  }, [html]);

  if (!html.trim()) {
    return <p className="flex-1 p-6 text-center text-sm text-[hsl(var(--muted))]">Sin documentación todavía.</p>;
  }
  return (
    <div ref={ref} className={`min-h-48 flex-1 overflow-auto p-4 text-sm ${PROSE}`}
      dangerouslySetInnerHTML={{ __html: html }} />
  );
}

interface Props {
  slug: string;
  initialNotes: string;
  onClose: () => void;
  onSaved: () => void;
}

export function DocModal({ slug, initialNotes, onClose, onSaved }: Props) {
  const [html, setHtml] = useState(initialNotes);
  const [mode, setMode] = useState<"preview" | "edit">(initialNotes.trim() ? "preview" : "edit");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api.updateViewNotes(slug, html);
      onSaved();
      setMode("preview"); // show the result with clickable links
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl border shadow-xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Documentación de la vista</h2>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border p-0.5 text-xs">
              <button className={`flex items-center gap-1 rounded px-2 py-1 ${mode === "preview" ? "bg-black/10 dark:bg-white/10 font-medium" : ""}`}
                onClick={() => setMode("preview")}><Eye size={13} /> Vista previa</button>
              <button className={`flex items-center gap-1 rounded px-2 py-1 ${mode === "edit" ? "bg-black/10 dark:bg-white/10 font-medium" : ""}`}
                onClick={() => setMode("edit")}><Pencil size={13} /> Editar</button>
            </div>
            <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
          </div>
        </div>

        {mode === "edit"
          ? <RichTextEditor initial={html} onChange={setHtml} />
          : <Preview html={html} />}

        <div className="flex justify-end gap-2 border-t px-4 py-3">
          {mode === "edit" ? (
            <>
              <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
              <button className="btn btn-primary" disabled={saving} onClick={save}>
                {saving ? "Guardando…" : "Guardar"}
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost" onClick={onClose}>Cerrar</button>
              <button className="btn btn-primary" onClick={() => setMode("edit")}><Pencil size={15} /> Editar</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

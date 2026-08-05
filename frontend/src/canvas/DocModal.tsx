import {
  Bold, Heading, Italic, List, ListOrdered, Link as LinkIcon, Redo2, Underline, X,
} from "lucide-react";
import { useRef, useState, type ReactNode } from "react";

import { api } from "../lib/api";

// Minimal WYSIWYG built on contentEditable + execCommand — no external dependency
// (keeps the bundle small and avoids the corporate npm proxy). Stores HTML.
function RichTextEditor({ initial, onChange }: { initial: string; onChange: (html: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);

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
        className="prose-sm min-h-48 flex-1 overflow-auto p-3 text-sm focus:outline-none [&_h3]:mb-1 [&_h3]:mt-2 [&_h3]:text-base [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:text-[hsl(var(--accent))] [&_a]:underline"
        dangerouslySetInnerHTML={{ __html: initial }}
        onInput={(e) => onChange(e.currentTarget.innerHTML)}
      />
    </div>
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
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api.updateViewNotes(slug, html);
      onSaved();
      onClose();
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
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>
        <RichTextEditor initial={initialNotes} onChange={setHtml} />
        <div className="flex justify-end gap-2 border-t px-4 py-3">
          <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={saving} onClick={save}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { ChevronDown, Copy, Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const FORMATS: { label: string; href: (slug: string) => string; file: (slug: string) => string }[] = [
  { label: "ArchiMate (Open Exchange XML)", href: (s) => `/api/v1/export/archimate?view=${s}`, file: (s) => `${s}.archimate.xml` },
  { label: "BPMN 2.0 XML", href: (s) => `/api/v1/export/bpmn?view=${s}`, file: (s) => `${s}.bpmn` },
  { label: "XMI (UML)", href: (s) => `/api/v1/export/xmi?view=${s}`, file: (s) => `${s}.xmi` },
  { label: "SVG", href: (s) => `/api/v1/export/image?view=${s}&format=svg`, file: (s) => `${s}.svg` },
  { label: "Mermaid (.mmd)", href: (s) => `/api/v1/export/mermaid?view=${s}`, file: (s) => `${s}.mmd` },
];

export function ExportMenu({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button className="btn btn-ghost" onClick={() => setOpen((v) => !v)} title="Exportar">
        <Download size={15} /> <span className="hidden lg:inline">Exportar</span> <ChevronDown size={13} />
      </button>
      {open && (
        <div className="surface absolute right-0 z-20 mt-1 w-64 rounded-md border py-1 shadow-lg">
          {FORMATS.map((f) => (
            <a
              key={f.label}
              href={f.href(slug)}
              download={f.file(slug)}
              className="block px-3 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => setOpen(false)}
            >
              {f.label}
            </a>
          ))}
          <div className="my-1 border-t" />
          <button
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5"
            onClick={async () => {
              setOpen(false);
              const txt = await fetch(`/api/v1/export/mermaid?view=${slug}`).then((r) => r.text());
              await navigator.clipboard.writeText(txt).catch(() => {});
            }}
          >
            <Copy size={14} /> Copiar Mermaid (para IA)
          </button>
        </div>
      )}
    </div>
  );
}

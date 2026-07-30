import type { Registry } from "../lib/types";

interface Props {
  from: string;
  to: string;
  lang: string;
  registry?: Registry;
  onPick: (kind: string) => void;
  onCancel: () => void;
}

// Relation kinds valid for the view's language (registry matrix, SPEC §4.2).
export function RelationPicker({ from, to, lang, registry, onPick, onCancel }: Props) {
  const kinds = registry
    ? Object.entries(registry.relations).filter(([, m]) => m[lang as keyof typeof m]).map(([k]) => k)
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onCancel}>
      <div className="surface w-80 rounded-lg border p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-semibold">Nueva relación</h3>
        <p className="mt-1 text-sm text-[hsl(var(--muted))]">
          <code>{from}</code> → <code>{to}</code>
        </p>
        <div className="mt-3 grid grid-cols-2 gap-1.5">
          {kinds.map((k) => (
            <button key={k} onClick={() => onPick(k)}
              className="btn btn-ghost justify-start text-sm">
              {k}
            </button>
          ))}
        </div>
        <button className="btn btn-ghost mt-3 w-full justify-center" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

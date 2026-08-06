// Reusable sortable + filterable data grid. Click a header to sort (asc → desc →
// none); the search box filters across all column values.
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  get: (row: T) => string | number; // value used for sort + filter
  render?: (row: T) => ReactNode; // optional custom cell
  sortable?: boolean; // default true
  className?: string;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  initialSort?: string;
  filterPlaceholder?: string;
  empty?: ReactNode;
  actions?: (row: T) => ReactNode;
  toolbar?: ReactNode;
}

export function DataTable<T>({
  columns, rows, rowKey, initialSort, filterPlaceholder = "Filtrar…", empty, actions, toolbar,
}: Props<T>) {
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(initialSort ?? null);
  const [dir, setDir] = useState<"asc" | "desc">("asc");

  const view = useMemo(() => {
    const needle = q.trim().toLowerCase();
    let out = needle
      ? rows.filter((r) => columns.some((c) => String(c.get(r)).toLowerCase().includes(needle)))
      : rows;
    const col = sortKey ? columns.find((c) => c.key === sortKey) : null;
    if (col) {
      out = [...out].sort((a, b) => {
        const va = col.get(a);
        const vb = col.get(b);
        const cmp =
          typeof va === "number" && typeof vb === "number"
            ? va - vb
            : String(va).localeCompare(String(vb), undefined, { numeric: true });
        return dir === "asc" ? cmp : -cmp;
      });
    }
    return out;
  }, [rows, columns, q, sortKey, dir]);

  function toggleSort(key: string) {
    if (sortKey !== key) { setSortKey(key); setDir("asc"); }
    else if (dir === "asc") setDir("desc");
    else setSortKey(null); // third click clears sorting
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-48 flex-1">
          <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
          <input className="input w-full pl-8" placeholder={filterPlaceholder} value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        {toolbar}
      </div>

      <div className="surface overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-[hsl(var(--muted))]">
            <tr>
              {columns.map((c) => (
                <th key={c.key} className={`px-4 py-2 font-medium ${c.className ?? ""}`}>
                  {c.sortable === false ? (
                    c.header
                  ) : (
                    <button className="inline-flex items-center gap-1 hover:text-[hsl(var(--fg))]" onClick={() => toggleSort(c.key)}>
                      {c.header}
                      {sortKey === c.key
                        ? dir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                        : <ArrowUpDown size={11} className="opacity-40" />}
                    </button>
                  )}
                </th>
              ))}
              {actions && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {view.map((r) => (
              <tr key={rowKey(r)} className="border-b last:border-0">
                {columns.map((c) => (
                  <td key={c.key} className={`px-4 py-2 ${c.className ?? ""}`}>
                    {c.render ? c.render(r) : String(c.get(r))}
                  </td>
                ))}
                {actions && <td className="px-4 py-2 text-right">{actions(r)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
        {view.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[hsl(var(--muted))]">{empty ?? "Sin resultados."}</div>
        )}
      </div>
    </div>
  );
}

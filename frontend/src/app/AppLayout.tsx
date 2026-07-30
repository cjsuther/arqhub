import { Boxes, LayoutGrid, Moon, Network, Search, Sun } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useTheme } from "./theme";

const NAV = [
  { to: "/catalog", label: "Catálogo", icon: Boxes },
  { to: "/views", label: "Vistas", icon: LayoutGrid },
];

export function AppLayout() {
  const { theme, toggle } = useTheme();
  return (
    <div className="flex h-full">
      <aside className="surface flex w-56 flex-col border-r">
        <div className="flex items-center gap-2 px-4 py-4 text-lg font-bold">
          <Network className="text-[hsl(var(--accent))]" size={22} />
          ArqHub
        </div>
        <nav className="flex flex-col gap-1 px-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `btn justify-start ${isActive ? "btn-primary" : "btn-ghost !border-transparent"}`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto p-3 text-xs text-[hsl(var(--muted))]">
          Model-first · IA-first
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="surface flex items-center gap-3 border-b px-4 py-2.5">
          <div className="relative flex-1 max-w-md">
            <Search
              size={16}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]"
            />
            <input className="input w-full pl-8" placeholder="Buscar…  (⌘K)" disabled />
          </div>
          <button className="btn btn-ghost" onClick={toggle} title="Cambiar tema">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <div className="badge bg-black/5 dark:bg-white/10">BNA</div>
        </header>

        <main className="min-h-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

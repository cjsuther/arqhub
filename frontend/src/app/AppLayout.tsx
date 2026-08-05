import { useQuery } from "@tanstack/react-query";
import {
  Boxes, CheckSquare, LayoutGrid, Menu, Moon, Network, Search, Shapes, Sparkles, Sun, Users,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { api } from "../lib/api";
import { useTheme } from "./theme";

const NAV = [
  { to: "/catalog", label: "Catálogo", icon: Boxes },
  { to: "/views", label: "Vistas", icon: LayoutGrid },
  { to: "/approvals", label: "Aprobaciones", icon: CheckSquare },
  { to: "/analysis", label: "Análisis", icon: Sparkles },
  { to: "/mappings", label: "Mapeos", icon: Shapes },
];

const ROLE_LABEL: Record<string, string> = {
  viewer: "Lector", editor: "Editor", approver: "Aprobador", admin: "Administrador",
};

export function AppLayout() {
  const { theme, toggle } = useTheme();
  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const nav = me.data?.role === "admin" ? [...NAV, { to: "/users", label: "Usuarios", icon: Users }] : NAV;

  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("arqhub:sidebar:collapsed") === "1");
  const toggleSidebar = () =>
    setCollapsed((c) => { const n = !c; localStorage.setItem("arqhub:sidebar:collapsed", n ? "1" : "0"); return n; });

  return (
    <div className="flex h-full">
      <aside className={`surface flex shrink-0 flex-col border-r transition-[width] ${collapsed ? "w-14" : "w-56"}`}>
        <div className="flex items-center gap-2 px-3 py-4 text-lg font-bold">
          <button className="rounded p-1 hover:bg-black/5 dark:hover:bg-white/5" onClick={toggleSidebar}
            title={collapsed ? "Expandir menú" : "Colapsar menú"}>
            <Menu size={20} className="text-[hsl(var(--accent))]" />
          </button>
          {!collapsed && <span className="flex items-center gap-2"><Network size={18} className="text-[hsl(var(--accent))]" /> ArqHub</span>}
        </div>
        <nav className="flex flex-col gap-1 px-2">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} title={label}
              className={({ isActive }) =>
                `btn ${collapsed ? "justify-center !px-0" : "justify-start"} ${isActive ? "btn-primary" : "btn-ghost !border-transparent"}`
              }>
              <Icon size={18} />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>
        {!collapsed && (
          <div className="mt-auto p-3 text-xs text-[hsl(var(--muted))]">Model-first · IA-first</div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="surface flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
          <div className="relative hidden min-w-40 flex-1 sm:block">
            <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
            <input className="input w-full pl-8" placeholder="Buscar…  (⌘K)" disabled />
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button className="btn btn-ghost" onClick={toggle} title="Cambiar tema">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {me.data && (
              <div className="hidden items-center gap-2 sm:flex" title={me.data.email}>
                <span className="max-w-32 truncate text-sm font-medium">{me.data.display_name}</span>
                <span className="badge bg-black/5 dark:bg-white/10">{ROLE_LABEL[me.data.role] ?? me.data.role}</span>
              </div>
            )}
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import {
  Bell, Boxes, CheckSquare, LayoutGrid, Menu, Moon, Network, Search, Shapes, Sparkles, Sun, Users,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

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
  const navigate = useNavigate();
  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const unread = useQuery({
    queryKey: ["notifications", "count"], queryFn: api.unreadCount, refetchInterval: 30_000,
  });
  const nav = me.data?.role === "admin" ? [...NAV, { to: "/users", label: "Usuarios", icon: Users }] : NAV;

  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("arqhub:sidebar:collapsed") === "1");
  const toggleSidebar = () =>
    setCollapsed((c) => { const n = !c; localStorage.setItem("arqhub:sidebar:collapsed", n ? "1" : "0"); return n; });

  return (
    <div className="flex h-full">
      <aside className={`surface flex shrink-0 flex-col border-r transition-[width] ${collapsed ? "w-14" : "w-56"}`}>
        <div className="flex items-center gap-2 px-3 py-4">
          <button className="rounded-lg p-1.5 hover:bg-black/5 dark:hover:bg-white/5" onClick={toggleSidebar}
            title={collapsed ? "Expandir menú" : "Colapsar menú"}>
            <Menu size={18} />
          </button>
          {!collapsed && (
            <span className="flex items-center gap-2 text-lg font-extrabold tracking-tight">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-[hsl(var(--accent))] to-[hsl(var(--accent-2))] text-white shadow-sm">
                <Network size={15} />
              </span>
              <span className="brand-gradient">ArqHub</span>
            </span>
          )}
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
          <div className="mt-auto flex items-center gap-2 p-3 text-xs text-[hsl(var(--muted))]">
            <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-br from-[hsl(var(--accent))] to-[hsl(var(--accent-2))]" />
            Model-first · IA-first
          </div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="surface flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
          <div className="relative hidden min-w-40 flex-1 sm:block">
            <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
            <input className="input w-full pl-8" placeholder="Buscar…  (⌘K)" disabled />
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button className="btn btn-ghost relative" onClick={() => navigate("/notifications")} title="Notificaciones">
              <Bell size={16} />
              {!!unread.data && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-medium text-white">
                  {unread.data > 9 ? "9+" : unread.data}
                </span>
              )}
            </button>
            <button className="btn btn-ghost" onClick={toggle} title="Cambiar tema">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {me.data && (
              <NavLink to="/profile" className="hidden items-center gap-2 rounded px-1.5 py-1 hover:bg-black/5 dark:hover:bg-white/5 sm:flex"
                title="Mi perfil y tokens">
                <span className="max-w-32 truncate text-sm font-medium">{me.data.display_name}</span>
                <span className="badge bg-black/5 dark:bg-white/10">{ROLE_LABEL[me.data.role] ?? me.data.role}</span>
              </NavLink>
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

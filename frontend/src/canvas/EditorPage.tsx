import "@xyflow/react/dist/style.css";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Background,
  ConnectionMode,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Node,
} from "@xyflow/react";
import { ArrowLeft, FileText, History, LayoutGrid, Magnet, MessageSquare, Redo2, Save, Undo2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../lib/api";
import type { Element, Lifecycle } from "../lib/types";
import { StatusBadge, formatDate, langLabel } from "../lib/ui";
import { ArchiMateNode, type NodeStyleOverride } from "./ArchiMateNode";
import { CanvasContextMenu, type MenuTarget } from "./CanvasContextMenu";
import { CommentsPanel } from "./CommentsPanel";
import { DocModal } from "./DocModal";
import { VersionsModal } from "./VersionsModal";
import { NAV_PROP, linkedView } from "./drilldown";
import { ExportMenu } from "./ExportMenu";
import { GovernanceControls } from "./GovernanceControls";
import { EdgeMarkers } from "./markers";
import { CATALOG_DND, Palette } from "./Palette";
import { PoolNodeView } from "./PoolNode";
import { PropertiesPanel } from "./PropertiesPanel";
import { RelationEdge, type RelEdge } from "./RelationEdge";
import { RelationPicker } from "./RelationPicker";
import { buildPoolNodes, hasPools, poolKind, type CanvasNode } from "./poolLayout";
import { NODE_H, NODE_W, layoutNodes } from "./layout";

type CanvasSnapshot = { nodes: CanvasNode[]; edgeStyles: Record<string, { stroke?: string }> };

const GRID = 18; // snap grid + background dot spacing

function EditorInner() {
  const { slug = "" } = useParams();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const viewGraph = useQuery({ queryKey: ["view-graph", slug], queryFn: () => api.getViewGraph(slug) });
  const views = useQuery({ queryKey: ["views"], queryFn: api.listViews });

  const [nodes, setNodes, onNodesChange] = useNodesState<CanvasNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<RelEdge>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [pending, setPending] = useState<{ from: string; to: string } | null>(null);
  const [saved, setSaved] = useState(false);
  const [menu, setMenu] = useState<{ x: number; y: number; target: MenuTarget } | null>(null);
  const [overlay, setOverlay] = useState<"versions" | "doc" | null>(null);
  const [showComments, setShowComments] = useState(false);
  const [snap, setSnap] = useState(false);
  // Per-view edge colour overrides (persisted in the view layout, keyed by relation slug).
  const [edgeStyles, setEdgeStyles] = useState<Record<string, { stroke?: string }>>({});
  const rf = useReactFlow();

  const commentCount = useQuery({
    queryKey: ["comments", slug],
    queryFn: () => api.listComments(slug),
    select: (c) => c.length,
  });

  // Mirror node positions so a refetch (add element / new relation) never
  // clobbers manual layout: existing nodes keep position, only new ones auto-layout.
  const posRef = useRef<Record<string, { x: number; y: number }>>({});
  useEffect(() => {
    for (const n of nodes) posRef.current[n.id] = n.position;
  }, [nodes]);

  const refetch = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["view-graph", slug] });
    qc.invalidateQueries({ queryKey: ["elements"] });
  }, [qc, slug]);

  // Build React Flow nodes/edges whenever the view graph or registry changes.
  useEffect(() => {
    const vg = viewGraph.data;
    const reg = registry.data;
    if (!vg || !reg) return;
    let cancelled = false;
    past.current = []; // model reloaded → presentation history no longer applies
    future.current = [];

    // Presentation overrides saved in the layout: node colours (keyed by element
    // slug) and edge colours (keyed by relation slug, x/y/w/h = 0).
    const relSlugs = new Set(vg.relations.map((r) => r.slug));
    const nodeStyleMap: Record<string, NodeStyleOverride> = {};
    const loadedEdgeStyles: Record<string, { stroke?: string }> = {};
    for (const l of vg.layout) {
      const st = (l.style ?? {}) as NodeStyleOverride & { stroke?: string };
      if (relSlugs.has(l.element)) {
        if (st.stroke) loadedEdgeStyles[l.element] = { stroke: st.stroke };
      } else if (st.borderColor || st.background) {
        nodeStyleMap[l.element] = { borderColor: st.borderColor, background: st.background };
      }
    }
    setEdgeStyles(loadedEdgeStyles);

    (async () => {
      // BPMN views with pools/lanes → nested swimlane layout (SPEC §8.2, §16).
      if (vg.view.lang === "bpmn" && hasPools(vg, reg)) {
        if (cancelled) return;
        setNodes(buildPoolNodes(vg, reg));
      } else {
        const positions: Record<string, { x: number; y: number }> = {};
        for (const l of vg.layout) positions[l.element] = { x: l.x, y: l.y };
        for (const [id, p] of Object.entries(posRef.current)) positions[id] = p; // manual wins

        const missing = vg.elements.filter((e) => !positions[e.slug]);
        if (missing.length) {
          const elk = await layoutNodes(
            vg.elements.map((e) => ({ id: e.slug })),
            vg.relations.map((r) => ({ source: r.from, target: r.to })),
          );
          for (const e of missing) positions[e.slug] = elk[e.slug] ?? { x: 0, y: 0 };
        }
        if (cancelled) return;

        setNodes(
          vg.elements.map((e) => ({
            id: e.slug,
            type: "archimate",
            position: positions[e.slug],
            data: {
              element: e,
              layer: reg.kinds[e.kind]?.layer ?? "application",
              lang: vg.view.lang,
              projection: reg.kinds[e.kind]?.mappings[vg.view.lang] ?? null,
              style: nodeStyleMap[e.slug],
            },
          })),
        );
      }
      // In pool mode, the pool→member assignment is shown by nesting, not an edge.
      const poolIdSet = new Set(vg.elements.filter((e) => poolKind(reg, e.kind)).map((e) => e.slug));
      const inPoolMode = vg.view.lang === "bpmn" && poolIdSet.size > 0;
      const visibleRelations = inPoolMode
        ? vg.relations.filter((r) => !(r.kind === "assignment" && poolIdSet.has(r.from)))
        : vg.relations;

      // Count/index edges that share the same (unordered) node pair so the edge
      // component can fan out parallel relations instead of overlapping them.
      const pairCount: Record<string, number> = {};
      for (const r of visibleRelations) {
        const k = [r.from, r.to].sort().join("|");
        pairCount[k] = (pairCount[k] ?? 0) + 1;
      }
      const pairSeen: Record<string, number> = {};
      setEdges(
        visibleRelations.map((r) => {
          const k = [r.from, r.to].sort().join("|");
          const parallelIndex = (pairSeen[k] = (pairSeen[k] ?? -1) + 1);
          return {
            id: r.slug,
            type: "relation",
            source: r.from,
            target: r.to,
            data: {
              kind: r.kind, label: r.label, parallelIndex, parallelCount: pairCount[k],
              stroke: loadedEdgeStyles[r.slug]?.stroke,
            },
          };
        }),
      );
    })();
    return () => {
      cancelled = true;
    };
  }, [viewGraph.data, registry.data, setNodes, setEdges]);

  const nodeTypes = useMemo(() => ({ archimate: ArchiMateNode, pool: PoolNodeView }), []);
  const edgeTypes = useMemo(() => ({ relation: RelationEdge }), []);

  // Persist positions + presentation. Node rows carry their colour override in
  // `style`; edge colours are stored as zero-size rows keyed by relation slug.
  const save = useCallback(
    async (nodesArg: CanvasNode[] = nodes, edgeStylesArg = edgeStyles) => {
      const nodeRows = nodesArg.map((n) => {
        const w = (typeof n.width === "number" && n.width) || n.measured?.width || NODE_W;
        const h = (typeof n.height === "number" && n.height) || n.measured?.height || NODE_H;
        const style = ((n.data as { style?: NodeStyleOverride })?.style ?? {}) as Record<string, unknown>;
        return { element: n.id, x: n.position.x, y: n.position.y, w, h, parent: n.parentId ?? null, style };
      });
      const edgeRows = Object.entries(edgeStylesArg)
        .filter(([, st]) => st?.stroke)
        .map(([relSlug, st]) => ({ element: relSlug, x: 0, y: 0, w: 0, h: 0, parent: null, style: st as Record<string, unknown> }));
      await api.putLayout(slug, [...nodeRows, ...edgeRows]);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    },
    [slug, nodes, edgeStyles],
  );
  const persistLayout = useCallback(() => save(), [save]);

  // --- Undo/redo of canvas presentation (positions + colours) ---------------
  const past = useRef<CanvasSnapshot[]>([]);
  const future = useRef<CanvasSnapshot[]>([]);
  const [, bumpHist] = useState(0);
  const tickHist = () => bumpHist((t) => t + 1);

  const snapshot = (): CanvasSnapshot => ({
    nodes: nodes.map((n) => ({ ...n, position: { ...n.position }, data: { ...(n.data as object) } }) as CanvasNode),
    edgeStyles: { ...edgeStyles },
  });
  const pushHistory = () => {
    past.current.push(snapshot());
    if (past.current.length > 50) past.current.shift();
    future.current = [];
    tickHist();
  };
  const applySnapshot = (s: CanvasSnapshot) => {
    setNodes(s.nodes);
    setEdgeStyles(s.edgeStyles);
    setEdges((es) => es.map((e) => ({ ...e, data: { ...e.data!, stroke: s.edgeStyles[e.id]?.stroke } })));
    save(s.nodes, s.edgeStyles);
  };
  const undo = () => {
    if (!past.current.length) return;
    future.current.push(snapshot());
    applySnapshot(past.current.pop()!);
    tickHist();
  };
  const redo = () => {
    if (!future.current.length) return;
    past.current.push(snapshot());
    applySnapshot(future.current.pop()!);
    tickHist();
  };
  const histRef = useRef({ undo, redo });
  histRef.current = { undo, redo };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "z") {
        e.preventDefault();
        e.shiftKey ? histRef.current.redo() : histRef.current.undo();
      } else if (mod && e.key.toLowerCase() === "y") {
        e.preventDefault();
        histRef.current.redo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Drag a node into/out of a pool → (un)assign it (model-first) and re-nest.
  const onNodeDragStop = useCallback(
    async (_: unknown, node: Node) => {
      const reg = registry.data;
      const vgd = viewGraph.data;
      if (node.type === "pool" || !reg || !vgd) {
        persistLayout();
        return;
      }
      const poolIds = new Set(vgd.elements.filter((e) => poolKind(reg, e.kind)).map((e) => e.slug));
      const targetPool = rf.getIntersectingNodes(node).find((n) => n.type === "pool")?.id ?? null;
      const currentParent = node.parentId ?? null;
      if (targetPool === currentParent) {
        persistLayout();
        return;
      }
      // Remove any existing pool→node assignment, then add the new one.
      const toRemove = vgd.relations.filter(
        (r) => r.kind === "assignment" && r.to === node.id && poolIds.has(r.from),
      );
      for (const r of toRemove) await api.deleteRelationship(r.slug).catch(() => {});
      if (targetPool) {
        await api.createRelationship({ from: targetPool, to: node.id, kind: "assignment" }).catch(() => {});
      }
      refetch();
    },
    [rf, registry.data, viewGraph.data, persistLayout, refetch],
  );

  const onConnect = useCallback((c: Connection) => {
    if (c.source && c.target && c.source !== c.target) setPending({ from: c.source, to: c.target });
  }, []);

  // Drag & drop a catalog element from the palette onto the canvas at the cursor.
  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);
  const onDrop = useCallback(
    async (e: DragEvent) => {
      e.preventDefault();
      const elSlug = e.dataTransfer.getData(CATALOG_DND);
      const vgd = viewGraph.data;
      if (!elSlug || !vgd || vgd.view.include.elements.includes(elSlug)) return;
      const p = rf.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      // Seed the position so the rebuild places it where dropped (not via auto-layout).
      posRef.current[elSlug] = snap
        ? { x: Math.round(p.x / GRID) * GRID, y: Math.round(p.y / GRID) * GRID }
        : p;
      await api.addElementsToView(slug, vgd.view, [elSlug]);
      refetch();
    },
    [rf, viewGraph.data, slug, snap, refetch],
  );

  async function pickRelation(kind: string) {
    if (!pending) return;
    try {
      await api.createRelationship({ from: pending.from, to: pending.to, kind });
      refetch();
    } finally {
      setPending(null);
    }
  }

  // --- Context menu actions --------------------------------------------------
  function elementOf(node: { data?: unknown }): Element | undefined {
    return (node.data as { element?: Element } | undefined)?.element;
  }

  function applyNodeStyle(id: string, patch: NodeStyleOverride) {
    pushHistory();
    const next = nodes.map((n) =>
      n.id === id
        ? ({ ...n, data: { ...n.data, style: { ...(n.data as { style?: NodeStyleOverride }).style, ...patch } } } as CanvasNode)
        : n,
    );
    setNodes(next);
    save(next, edgeStyles);
  }

  async function changeLifecycle(elSlug: string, lc: Lifecycle) {
    await api.updateElement(elSlug, { lifecycle: lc });
    refetch();
  }

  async function linkView(element: Element, viewSlug: string | null) {
    const props: Record<string, string> = { ...element.properties };
    if (viewSlug) props[NAV_PROP] = viewSlug;
    else delete props[NAV_PROP];
    await api.updateElement(element.slug, { properties: props });
    refetch();
  }

  function goToLinked(element: Element) {
    const target = linkedView(element);
    if (target) navigate(`/views/${target}/edit`);
  }

  async function removeFromView(elSlug: string) {
    const vgd = viewGraph.data;
    if (!vgd) return;
    await api.removeElementFromView(slug, vgd.view, elSlug).catch(() => {});
    refetch();
  }

  function setEdgeColor(relSlug: string, color: string | null) {
    pushHistory();
    const next = { ...edgeStyles };
    if (color) next[relSlug] = { stroke: color };
    else delete next[relSlug];
    setEdgeStyles(next);
    setEdges((es) => es.map((e) => (e.id === relSlug ? { ...e, data: { ...e.data!, stroke: color ?? undefined } } : e)));
    save(nodes, next);
  }

  async function deleteEdge(relSlug: string) {
    await api.deleteRelationship(relSlug).catch(() => {});
    refetch();
  }

  async function renameEdge(relSlug: string, label: string | null) {
    await api.updateRelationship(relSlug, { label });
    refetch();
  }

  async function organize() {
    const vgd = viewGraph.data;
    const reg = registry.data;
    if (vgd && reg && vgd.view.lang === "bpmn" && hasPools(vgd, reg)) {
      setNodes(buildPoolNodes({ ...vgd, layout: [] }, reg)); // re-flow pools from scratch
      return;
    }
    const pos = await layoutNodes(
      nodes.map((n) => ({ id: n.id })),
      edges.map((e) => ({ source: e.source, target: e.target })),
    );
    setNodes((ns) => ns.map((n) => ({ ...n, position: pos[n.id] ?? n.position })));
  }

  const vg = viewGraph.data;
  const selectedElement: Element | null = vg?.elements.find((e) => e.slug === selected) ?? null;
  const inView = new Set(vg?.elements.map((e) => e.slug) ?? []);

  if (viewGraph.isError)
    return <div className="p-6 text-sm text-red-500">No se pudo cargar la vista «{slug}».</div>;

  return (
    <div className="flex h-full flex-col">
      <header className="surface flex items-center gap-3 border-b px-4 py-2">
        <Link to="/views" className="btn btn-ghost"><ArrowLeft size={16} /></Link>
        <div className="min-w-0">
          <div className="truncate font-semibold">{vg?.view.name ?? "…"}</div>
          <div className="text-xs text-[hsl(var(--muted))]">
            {vg && `${langLabel(vg.view.lang)} · v${vg.view.current_version}`}
          </div>
        </div>
        {vg && (
          <div className="flex flex-col leading-tight">
            <StatusBadge value={vg.view.status} />
            {vg.view.status_changed_at && (
              <span className="mt-0.5 text-[10px] text-[hsl(var(--muted))]">
                {vg.view.status_changed_by_name ? `${vg.view.status_changed_by_name} · ` : ""}{formatDate(vg.view.status_changed_at)}
              </span>
            )}
          </div>
        )}
        {vg && <GovernanceControls view={vg.view} onChanged={refetch} />}
        <div className="ml-auto flex items-center gap-2">
          <button className="btn btn-ghost" onClick={() => setOverlay("versions")} title="Comparar versiones">
            <History size={15} /> Versiones
          </button>
          <button className="btn btn-ghost" onClick={() => setOverlay("doc")} title="Documentación (texto enriquecido)">
            <FileText size={15} /> Documentación
          </button>
          <button className="btn btn-ghost relative" onClick={() => setShowComments((s) => !s)} title="Comentarios">
            <MessageSquare size={15} /> Comentarios
            {!!commentCount.data && (
              <span className="ml-0.5 rounded-full bg-[hsl(var(--accent))] px-1.5 text-[10px] text-white">{commentCount.data}</span>
            )}
          </button>
          <ExportMenu slug={slug} />
          <div className="flex">
            <button className="btn btn-ghost !px-2" onClick={undo} disabled={past.current.length === 0}
              title="Deshacer (Ctrl+Z)"><Undo2 size={15} /></button>
            <button className="btn btn-ghost !px-2" onClick={redo} disabled={future.current.length === 0}
              title="Rehacer (Ctrl+Shift+Z)"><Redo2 size={15} /></button>
          </div>
          <button className={`btn ${snap ? "btn-primary" : "btn-ghost"}`} onClick={() => setSnap((s) => !s)}
            title="Ajustar a la grilla">
            <Magnet size={15} /> Grilla
          </button>
          <button className="btn btn-ghost" onClick={organize}><LayoutGrid size={15} /> Organizar</button>
          <button className="btn btn-primary" onClick={persistLayout}>
            <Save size={15} /> {saved ? "Guardado" : "Guardar layout"}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {vg && <Palette view={vg.view} registry={registry.data} inView={inView} onChanged={refetch} />}
        <div className="relative min-w-0 flex-1" onDrop={onDrop} onDragOver={onDragOver}>
          <EdgeMarkers />
          <ReactFlow<CanvasNode, RelEdge>
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStart={() => pushHistory()}
            onNodeDragStop={onNodeDragStop}
            onNodeClick={(_, n) => setSelected(n.id)}
            onNodeDoubleClick={(_, n) => { const el = elementOf(n); if (el) goToLinked(el); }}
            onNodeContextMenu={(e, n) => {
              const el = elementOf(n);
              if (!el) return;
              e.preventDefault();
              setSelected(n.id);
              setMenu({ x: e.clientX, y: e.clientY, target: { type: "node", element: el, style: (n.data as { style?: NodeStyleOverride }).style } });
            }}
            onEdgeContextMenu={(e, ed) => {
              e.preventDefault();
              setMenu({ x: e.clientX, y: e.clientY, target: { type: "edge", slug: ed.id, kind: ed.data?.kind ?? "association", label: ed.data?.label, stroke: ed.data?.stroke } });
            }}
            onPaneClick={() => { setSelected(null); setMenu(null); }}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            connectionMode={ConnectionMode.Loose}
            snapToGrid={snap}
            snapGrid={[GRID, GRID]}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#cbd5e1" gap={GRID} />
            <Controls />
            <MiniMap pannable zoomable className="!bg-white" />
          </ReactFlow>
        </div>
        <PropertiesPanel element={selectedElement} onSaved={refetch} />
        {showComments && <CommentsPanel slug={slug} onClose={() => setShowComments(false)} />}
      </div>

      {pending && (
        <RelationPicker
          from={pending.from}
          to={pending.to}
          lang={vg?.view.lang ?? "archimate"}
          registry={registry.data}
          onPick={pickRelation}
          onCancel={() => setPending(null)}
        />
      )}

      {menu && (
        <CanvasContextMenu
          x={menu.x}
          y={menu.y}
          target={menu.target}
          views={views.data ?? []}
          currentViewSlug={slug}
          onClose={() => setMenu(null)}
          onNodeStyle={(patch) => menu.target.type === "node" && applyNodeStyle(menu.target.element.slug, patch)}
          onLifecycle={(lc) => menu.target.type === "node" && changeLifecycle(menu.target.element.slug, lc)}
          onLink={(v) => menu.target.type === "node" && linkView(menu.target.element, v)}
          onNavigate={() => menu.target.type === "node" && goToLinked(menu.target.element)}
          onRemoveFromView={() => menu.target.type === "node" && removeFromView(menu.target.element.slug)}
          onEdgeStroke={(c) => menu.target.type === "edge" && setEdgeColor(menu.target.slug, c)}
          onRenameEdge={(l) => menu.target.type === "edge" && renameEdge(menu.target.slug, l)}
          onDeleteEdge={() => menu.target.type === "edge" && deleteEdge(menu.target.slug)}
        />
      )}

      {overlay === "versions" && <VersionsModal slug={slug} onClose={() => setOverlay(null)} />}
      {overlay === "doc" && (
        <DocModal slug={slug} initialNotes={vg?.view.notes ?? ""} onClose={() => setOverlay(null)} onSaved={refetch} />
      )}
    </div>
  );
}

export function EditorPage() {
  return (
    <ReactFlowProvider>
      <EditorInner />
    </ReactFlowProvider>
  );
}

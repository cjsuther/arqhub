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
  type Connection,
} from "@xyflow/react";
import { ArrowLeft, LayoutGrid, Save } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../lib/api";
import type { Element } from "../lib/types";
import { StatusBadge, langLabel } from "../lib/ui";
import { ArchiMateNode, type ArchiNode } from "./ArchiMateNode";
import { ExportMenu } from "./ExportMenu";
import { GovernanceControls } from "./GovernanceControls";
import { EdgeMarkers } from "./markers";
import { Palette } from "./Palette";
import { PropertiesPanel } from "./PropertiesPanel";
import { RelationEdge, type RelEdge } from "./RelationEdge";
import { RelationPicker } from "./RelationPicker";
import { NODE_H, NODE_W, layoutNodes } from "./layout";

function EditorInner() {
  const { slug = "" } = useParams();
  const qc = useQueryClient();

  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const viewGraph = useQuery({ queryKey: ["view-graph", slug], queryFn: () => api.getViewGraph(slug) });

  const [nodes, setNodes, onNodesChange] = useNodesState<ArchiNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<RelEdge>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [pending, setPending] = useState<{ from: string; to: string } | null>(null);
  const [saved, setSaved] = useState(false);

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

    (async () => {
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
          data: { element: e, layer: reg.kinds[e.kind]?.layer ?? "application", lang: vg.view.lang },
        })),
      );
      setEdges(
        vg.relations.map((r) => ({
          id: r.slug,
          type: "relation",
          source: r.from,
          target: r.to,
          data: { kind: r.kind, label: r.label },
        })),
      );
    })();
    return () => {
      cancelled = true;
    };
  }, [viewGraph.data, registry.data, setNodes, setEdges]);

  const nodeTypes = useMemo(() => ({ archimate: ArchiMateNode }), []);
  const edgeTypes = useMemo(() => ({ relation: RelationEdge }), []);

  const persistLayout = useCallback(async () => {
    await api.putLayout(
      slug,
      nodes.map((n) => ({ element: n.id, x: n.position.x, y: n.position.y, w: NODE_W, h: NODE_H, style: {} })),
    );
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }, [slug, nodes]);

  const onConnect = useCallback((c: Connection) => {
    if (c.source && c.target && c.source !== c.target) setPending({ from: c.source, to: c.target });
  }, []);

  async function pickRelation(kind: string) {
    if (!pending) return;
    try {
      await api.createRelationship({ from: pending.from, to: pending.to, kind });
      refetch();
    } finally {
      setPending(null);
    }
  }

  async function organize() {
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
        {vg && <StatusBadge value={vg.view.status} />}
        {vg && <GovernanceControls view={vg.view} onChanged={refetch} />}
        <div className="ml-auto flex items-center gap-2">
          <ExportMenu slug={slug} />
          <button className="btn btn-ghost" onClick={organize}><LayoutGrid size={15} /> Organizar</button>
          <button className="btn btn-primary" onClick={persistLayout}>
            <Save size={15} /> {saved ? "Guardado" : "Guardar layout"}
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {vg && <Palette view={vg.view} registry={registry.data} inView={inView} onChanged={refetch} />}
        <div className="relative min-w-0 flex-1">
          <EdgeMarkers />
          <ReactFlow<ArchiNode, RelEdge>
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStop={persistLayout}
            onNodeClick={(_, n) => setSelected(n.id)}
            onPaneClick={() => setSelected(null)}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            connectionMode={ConnectionMode.Loose}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#cbd5e1" gap={18} />
            <Controls />
            <MiniMap pannable zoomable className="!bg-white" />
          </ReactFlow>
        </div>
        <PropertiesPanel element={selectedElement} onSaved={refetch} />
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

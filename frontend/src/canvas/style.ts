// Node colouring by ArchiMate layer + type icon (docs/archimate-notation.md, SPEC §8.2).
// ArchiMate is colour-neutral; ArqHub colours by layer (not by aspect like the book).
import {
  ArrowRight,
  Box,
  Circle,
  Database,
  Diamond,
  FileText,
  Flag,
  Plug,
  Server,
  Target,
  User,
  Users,
  Zap,
  type LucideIcon,
} from "lucide-react";

export interface LayerStyle {
  bg: string;
  border: string;
  text: string;
}

// Fixed light-mode diagram colours (ArchiMate views read as light regardless of app theme).
export const LAYER_STYLES: Record<string, LayerStyle> = {
  business: { bg: "#fdf3d0", border: "#e0b93f", text: "#7a5c00" },
  application: { bg: "#dcecfb", border: "#4f9dde", text: "#0b4a7a" },
  technology: { bg: "#d9f0d9", border: "#5cb85c", text: "#1f5e1f" },
  motivation: { bg: "#e7ddf7", border: "#9b7ede", text: "#4b2e83" },
  strategy: { bg: "#f7e6cf", border: "#d99b4e", text: "#7a4a12" },
  implementation: { bg: "#fbe0ea", border: "#e06a99", text: "#7a1f47" },
};

export function layerStyle(layer?: string): LayerStyle {
  return LAYER_STYLES[layer ?? ""] ?? LAYER_STYLES.application;
}

const KIND_ICON: Record<string, LucideIcon> = {
  actor: User,
  role: Users,
  process: ArrowRight,
  task: Zap,
  event: Flag,
  gateway: Diamond,
  service: Circle,
  "app-component": Box,
  interface: Plug,
  "data-object": Database,
  node: Server,
  artifact: FileText,
  capability: Target,
  goal: Target,
};

export function kindIcon(kind: string): LucideIcon {
  return KIND_ICON[kind] ?? Box;
}

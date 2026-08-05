// Floating-edge geometry: attach an edge to the border of each node that faces
// the other node, so connectors touch the nearest side (not a fixed handle).
// Adapted from the React Flow "floating edges" example.
import { Position, type InternalNode, type Node } from "@xyflow/react";

interface Point {
  x: number;
  y: number;
}

// Intersection of the line between the two node centers with `node`'s rectangle.
function nodeIntersection(node: InternalNode<Node>, other: InternalNode<Node>): Point {
  const w = (node.measured?.width ?? 0) / 2;
  const h = (node.measured?.height ?? 0) / 2;
  const nx = node.internals.positionAbsolute.x;
  const ny = node.internals.positionAbsolute.y;
  const ox = other.internals.positionAbsolute.x + (other.measured?.width ?? 0) / 2;
  const oy = other.internals.positionAbsolute.y + (other.measured?.height ?? 0) / 2;

  const cx = nx + w;
  const cy = ny + h;
  if (w === 0 || h === 0) return { x: cx, y: cy };

  const xx1 = (ox - cx) / (2 * w) - (oy - cy) / (2 * h);
  const yy1 = (ox - cx) / (2 * w) + (oy - cy) / (2 * h);
  const a = 1 / (Math.abs(xx1) + Math.abs(yy1) || 1);
  const xx3 = a * xx1;
  const yy3 = a * yy1;
  return { x: w * (xx3 + yy3) + cx, y: h * (-xx3 + yy3) + cy };
}

// Which side of `node` the intersection point sits on.
function edgeSide(node: InternalNode<Node>, p: Point): Position {
  const nx = Math.round(node.internals.positionAbsolute.x);
  const ny = Math.round(node.internals.positionAbsolute.y);
  const px = Math.round(p.x);
  const py = Math.round(p.y);
  if (px <= nx + 1) return Position.Left;
  if (px >= nx + (node.measured?.width ?? 0) - 1) return Position.Right;
  if (py <= ny + 1) return Position.Top;
  return Position.Bottom;
}

export interface EdgeParams {
  sx: number;
  sy: number;
  tx: number;
  ty: number;
  sourcePos: Position;
  targetPos: Position;
}

export function getEdgeParams(source: InternalNode<Node>, target: InternalNode<Node>): EdgeParams {
  const s = nodeIntersection(source, target);
  const t = nodeIntersection(target, source);
  return {
    sx: s.x,
    sy: s.y,
    tx: t.x,
    ty: t.y,
    sourcePos: edgeSide(source, s),
    targetPos: edgeSide(target, t),
  };
}

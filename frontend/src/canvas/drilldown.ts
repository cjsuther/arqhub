// Drill-down: an element can link to a view (e.g. a process → its BPMN detail).
// Stored as a reserved element property so it travels with the model, not a
// single view's presentation — the same element drills to the same sub-view
// wherever it appears.
import type { Element } from "../lib/types";

export const NAV_PROP = "navigateTo";

export function linkedView(el: Element | null | undefined): string | null {
  return (el?.properties?.[NAV_PROP] as string | undefined) || null;
}

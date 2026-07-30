// SVG marker defs for ArchiMate relation ends (docs/archimate-notation.md).
// Mounted once in the editor; custom edges reference them via url(#id).
const STROKE = "#64748b";

export function EdgeMarkers() {
  return (
    <svg style={{ position: "absolute", width: 0, height: 0 }} aria-hidden>
      <defs>
        {/* Serving / Access / Influence — open arrow */}
        <marker id="am-arrow-open" markerWidth="12" markerHeight="12" refX="9" refY="4"
          orient="auto" markerUnits="userSpaceOnUse">
          <path d="M0,0 L9,4 L0,8" fill="none" stroke={STROKE} strokeWidth="1.3" />
        </marker>
        {/* Triggering / Flow / Assignment(end) — filled arrow */}
        <marker id="am-arrow-filled" markerWidth="12" markerHeight="12" refX="9" refY="4"
          orient="auto" markerUnits="userSpaceOnUse">
          <path d="M0,0 L9,4 L0,8 Z" fill={STROKE} />
        </marker>
        {/* Realization / Specialization — hollow triangle */}
        <marker id="am-tri-hollow" markerWidth="16" markerHeight="14" refX="12" refY="5"
          orient="auto" markerUnits="userSpaceOnUse">
          <path d="M0,0 L12,5 L0,10 Z" fill="white" stroke={STROKE} strokeWidth="1.2" />
        </marker>
        {/* Composition — filled diamond (at source) */}
        <marker id="am-diamond-filled" markerWidth="18" markerHeight="12" refX="1" refY="5"
          orient="auto-start-reverse" markerUnits="userSpaceOnUse">
          <path d="M0,5 L6,0 L12,5 L6,10 Z" fill={STROKE} />
        </marker>
        {/* Aggregation — hollow diamond (at source) */}
        <marker id="am-diamond-hollow" markerWidth="18" markerHeight="12" refX="1" refY="5"
          orient="auto-start-reverse" markerUnits="userSpaceOnUse">
          <path d="M0,5 L6,0 L12,5 L6,10 Z" fill="white" stroke={STROKE} strokeWidth="1.2" />
        </marker>
        {/* Assignment — filled ball (at source) */}
        <marker id="am-ball" markerWidth="10" markerHeight="10" refX="4" refY="4"
          orient="auto-start-reverse" markerUnits="userSpaceOnUse">
          <circle cx="4" cy="4" r="3.2" fill={STROKE} />
        </marker>
      </defs>
    </svg>
  );
}

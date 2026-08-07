import type { GenerationStatus } from "../types";

const LABELS: Record<GenerationStatus, string> = {
  pending:        "Queued…",
  generating_2d:  "Generating 2D concepts with Stable Diffusion…",
  generating_3d:  "Converting images to 3D meshes with TripoSR…",
  tagging:        "Tagging assets with LLaVA…",
  indexing:       "Indexing assets in vector database…",
  complete:       "Scene ready",
  failed:         "Generation failed",
};

const COLORS: Partial<Record<GenerationStatus, string>> = {
  complete: "#4ade80",
  failed:   "#f87171",
};

interface Props {
  status: GenerationStatus;
  error: string | null;
  duration: number | null;
}

export function StatusBar({ status, error, duration }: Props) {
  const color = COLORS[status] ?? "#a78bfa";
  return (
    <div style={styles.bar}>
      <span style={{ ...styles.dot, background: color }} />
      <span style={{ ...styles.label, color }}>
        {error ?? LABELS[status]}
      </span>
      {duration != null && status === "complete" && (
        <span style={styles.duration}>{duration.toFixed(1)}s</span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    position: "absolute",
    top: 20,
    left: "50%",
    transform: "translateX(-50%)",
    zIndex: 10,
    display: "flex",
    alignItems: "center",
    gap: 8,
    backdropFilter: "blur(10px)",
    background: "rgba(13,13,20,0.75)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 24,
    padding: "6px 16px",
    fontSize: 13,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  },
  label: {
    fontWeight: 500,
    letterSpacing: "0.01em",
  },
  duration: {
    marginLeft: 4,
    color: "rgba(255,255,255,0.35)",
    fontSize: 12,
  },
};

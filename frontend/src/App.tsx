import { useSceneJob } from "./hooks/useSceneJob";
import { PromptForm } from "./components/PromptForm";
import { SceneViewer } from "./components/SceneViewer";
import { StatusBar } from "./components/StatusBar";

export default function App() {
  const { response, loading, error, generate } = useSceneJob();

  const hasScene =
    response?.status === "complete" && response.scene_graph != null;

  return (
    <div style={styles.root}>
      {/* Header */}
      <header style={styles.header}>
        <span style={styles.logo}>RADA</span>
        <span style={styles.logoSub}>Spatial AI</span>
      </header>

      {/* 3D Canvas or empty state */}
      <div style={styles.canvas}>
        {hasScene ? (
          <SceneViewer scene={response!.scene_graph!} />
        ) : (
          <EmptyState />
        )}
      </div>

      {/* Status bar (visible once a job exists) */}
      {response && (
        <StatusBar
          status={response.status}
          error={error}
          duration={response.duration_seconds}
        />
      )}

      {/* Prompt input */}
      <PromptForm onSubmit={generate} disabled={loading} />
    </div>
  );
}

function EmptyState() {
  return (
    <div style={styles.empty}>
      <div style={styles.emptyGlow} />
      <p style={styles.emptyText}>
        Describe a scene below to begin spatial generation
      </p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    position: "relative",
    width: "100%",
    height: "100%",
    background: "#0d0d14",
    fontFamily:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    overflow: "hidden",
    color: "#e8e8f0",
  },
  header: {
    position: "absolute",
    top: 20,
    left: 24,
    zIndex: 10,
    display: "flex",
    alignItems: "baseline",
    gap: 6,
  },
  logo: {
    fontSize: 22,
    fontWeight: 800,
    letterSpacing: "0.12em",
    background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  logoSub: {
    fontSize: 11,
    fontWeight: 500,
    color: "rgba(255,255,255,0.3)",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  canvas: {
    width: "100%",
    height: "100%",
  },
  empty: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    flexDirection: "column",
    gap: 16,
    position: "relative",
  },
  emptyGlow: {
    position: "absolute",
    width: 400,
    height: 400,
    borderRadius: "50%",
    background:
      "radial-gradient(circle, rgba(108,99,255,0.12) 0%, transparent 70%)",
    pointerEvents: "none",
  },
  emptyText: {
    color: "rgba(255,255,255,0.25)",
    fontSize: 15,
    letterSpacing: "0.02em",
    textAlign: "center",
    maxWidth: 340,
    lineHeight: 1.6,
    position: "relative",
  },
};

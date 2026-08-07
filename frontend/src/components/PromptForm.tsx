import { useState } from "react";
import type { GenerationRequest, StyleTag } from "../types";

const STYLES: StyleTag[] = [
  "cozy", "industrial", "cyberpunk", "minimalist",
  "rustic", "futuristic", "fantasy", "realistic",
];

interface Props {
  onSubmit: (req: GenerationRequest) => void;
  disabled: boolean;
}

export function PromptForm({ onSubmit, disabled }: Props) {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState<StyleTag | "">("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    onSubmit({
      prompt: prompt.trim(),
      style: style || undefined,
      max_assets: 10,
    });
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.row}>
        <input
          style={styles.input}
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your scene… e.g. 'A cozy cyberpunk reading nook'"
          disabled={disabled}
        />
        <select
          style={styles.select}
          value={style}
          onChange={(e) => setStyle(e.target.value as StyleTag | "")}
          disabled={disabled}
        >
          <option value="">Any style</option>
          {STYLES.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
        <button style={styles.button} type="submit" disabled={disabled || !prompt.trim()}>
          {disabled ? "Generating…" : "Generate Scene"}
        </button>
      </div>
    </form>
  );
}

const styles: Record<string, React.CSSProperties> = {
  form: {
    position: "absolute",
    bottom: 32,
    left: "50%",
    transform: "translateX(-50%)",
    zIndex: 10,
    width: "min(720px, 90vw)",
  },
  row: {
    display: "flex",
    gap: 8,
    backdropFilter: "blur(12px)",
    background: "rgba(13,13,20,0.82)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 12,
    padding: "10px 12px",
  },
  input: {
    flex: 1,
    background: "transparent",
    border: "none",
    outline: "none",
    color: "#e8e8f0",
    fontSize: 15,
    fontFamily: "inherit",
  },
  select: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 8,
    color: "#b0b0c0",
    fontSize: 13,
    padding: "4px 8px",
    cursor: "pointer",
  },
  button: {
    background: "linear-gradient(135deg, #6c63ff, #9b59b6)",
    border: "none",
    borderRadius: 8,
    color: "#fff",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
    padding: "8px 20px",
    whiteSpace: "nowrap",
    opacity: 1,
    transition: "opacity 0.15s",
  },
};

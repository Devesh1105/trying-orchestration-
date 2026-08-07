/** TypeScript mirrors of the Pydantic backend schemas. */

export type GenerationStatus =
  | "pending"
  | "generating_2d"
  | "generating_3d"
  | "tagging"
  | "indexing"
  | "complete"
  | "failed";

export type StyleTag =
  | "cozy"
  | "industrial"
  | "cyberpunk"
  | "minimalist"
  | "rustic"
  | "futuristic"
  | "fantasy"
  | "realistic";

export type AnchorPoint = "floor" | "wall" | "ceiling" | "surface" | "floating";

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface AssetPlacement {
  asset_id: string;
  asset_name: string;
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
  glb_url: string | null;
  metadata: Record<string, unknown>;
}

export interface SceneGraph {
  id: string;
  title: string;
  description: string;
  style: StyleTag | null;
  ambient_light_intensity: number;
  background_color: string;
  assets: AssetPlacement[];
  room_dimensions: Vec3;
}

export interface GenerationResponse {
  job_id: string;
  status: GenerationStatus;
  scene_graph: SceneGraph | null;
  error: string | null;
  duration_seconds: number | null;
}

export interface GenerationRequest {
  prompt: string;
  style?: StyleTag;
  room_width?: number;
  room_depth?: number;
  room_height?: number;
  max_assets?: number;
  force_regenerate?: boolean;
}

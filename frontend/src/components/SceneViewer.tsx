import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import {
  Environment,
  Grid,
  OrbitControls,
  PerspectiveCamera,
  Stars,
} from "@react-three/drei";
import type { SceneGraph } from "../types";
import { AssetObject } from "./AssetObject";

const API_BASE = "";

interface Props {
  scene: SceneGraph;
}

export function SceneViewer({ scene }: Props) {
  const roomW = scene.room_dimensions.x;
  const roomD = scene.room_dimensions.z;

  const initialCamPos: [number, number, number] = useMemo(
    () => [roomW * 0.7, roomW * 0.5, roomD * 0.7],
    [roomW, roomD]
  );

  return (
    <Canvas shadows style={{ width: "100%", height: "100%" }}>
      <PerspectiveCamera makeDefault position={initialCamPos} fov={55} />
      <OrbitControls
        target={[0, 0.5, 0]}
        maxPolarAngle={Math.PI / 2 - 0.05}
        enableDamping
        dampingFactor={0.08}
      />

      {/* Lighting */}
      <ambientLight intensity={scene.ambient_light_intensity * 0.4} />
      <directionalLight
        castShadow
        position={[roomW * 0.6, roomW, roomD * 0.4]}
        intensity={scene.ambient_light_intensity}
        shadow-mapSize={[2048, 2048]}
      />
      <Environment preset="city" />

      {/* Background atmosphere */}
      <Stars radius={80} depth={40} count={3000} factor={3} fade />

      {/* Floor grid */}
      <Grid
        position={[0, 0, 0]}
        args={[roomW, roomD]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#2a2a3a"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#4a4a6a"
        fadeDistance={roomW * 2}
        infiniteGrid={false}
      />

      {/* Room floor plane (receives shadows) */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <planeGeometry args={[roomW, roomD]} />
        <meshStandardMaterial color="#111118" roughness={0.9} />
      </mesh>

      {/* Assets */}
      <Suspense fallback={null}>
        {scene.assets.map((placement) => (
          <AssetObject
            key={placement.asset_id}
            placement={placement}
            apiBase={API_BASE}
          />
        ))}
      </Suspense>
    </Canvas>
  );
}

import { useRef } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import type { Mesh } from "three";
import * as THREE from "three";
import type { AssetPlacement } from "../types";

interface Props {
  placement: AssetPlacement;
  apiBase: string;
}

export function AssetObject({ placement, apiBase }: Props) {
  const { position, rotation, scale, glb_url, asset_name } = placement;

  const url = glb_url
    ? glb_url.startsWith("http")
      ? glb_url
      : `${apiBase}/${glb_url}`
    : null;

  if (!url) return <FallbackBox placement={placement} />;

  return <GLBAsset url={url} position={position} rotation={rotation} scale={scale} name={asset_name} />;
}

function GLBAsset({
  url,
  position,
  rotation,
  scale,
  name,
}: {
  url: string;
  position: { x: number; y: number; z: number };
  rotation: { x: number; y: number; z: number };
  scale: { x: number; y: number; z: number };
  name: string;
}) {
  const { scene } = useGLTF(url);
  const deg = Math.PI / 180;

  return (
    <primitive
      object={scene.clone()}
      position={[position.x, position.y, position.z]}
      rotation={[rotation.x * deg, rotation.y * deg, rotation.z * deg]}
      scale={[scale.x, scale.y, scale.z]}
      name={name}
    />
  );
}

function FallbackBox({ placement }: { placement: AssetPlacement }) {
  const meshRef = useRef<Mesh>(null);
  const { position, rotation, scale } = placement;
  const deg = Math.PI / 180;

  // Gentle idle rotation so the placeholder is visually distinct
  useFrame((_, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.4;
  });

  return (
    <mesh
      ref={meshRef}
      position={[position.x, position.y + 0.5, position.z]}
      rotation={[rotation.x * deg, rotation.y * deg, rotation.z * deg]}
      scale={[scale.x, scale.y, scale.z]}
    >
      <boxGeometry args={[0.8, 0.8, 0.8]} />
      <meshStandardMaterial
        color="#6c63ff"
        emissive="#3b30a0"
        roughness={0.4}
        metalness={0.6}
        wireframe={false}
      />
    </mesh>
  );
}

/**
 * InteractiveBackground Component
 *
 * 3D background with wireframe shapes that:
 * - Double-tap spawns new shapes at the tap point
 * - Spawned shapes STAY and float permanently (don't fade away)
 * - They drift slowly and rotate, joining the existing floating shapes
 * - Starts with a few ambient shapes already floating
 */

import { useRef, useState, useCallback, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';
import { useTheme } from '../../context/ThemeContext';

// ─── Floating Shape (permanent, drifts and rotates) ───────────

function FloatingShape({
  geometry,
  position,
  color,
  speed,
  scale = 1,
}: {
  geometry: 'ico' | 'octa' | 'dodeca' | 'torus' | 'tetra' | 'box';
  position: [number, number, number];
  color: string;
  speed: [number, number, number];
  scale?: number;
}) {
  const ref = useRef<THREE.Mesh>(null!);

  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.x += speed[0];
    ref.current.rotation.y += speed[1];
    ref.current.rotation.z += speed[2];
    // Gentle float
    ref.current.position.y += Math.sin(state.clock.elapsedTime * 0.4 + ref.current.position.x) * 0.001;
  });

  const getGeometry = () => {
    switch (geometry) {
      case 'ico': return <icosahedronGeometry args={[1, 0]} />;
      case 'octa': return <octahedronGeometry args={[1, 0]} />;
      case 'dodeca': return <dodecahedronGeometry args={[1, 0]} />;
      case 'torus': return <torusGeometry args={[1, 0.3, 8, 16]} />;
      case 'tetra': return <tetrahedronGeometry args={[1, 0]} />;
      case 'box': return <boxGeometry args={[1, 1, 1]} />;
    }
  };

  return (
    <Float speed={0.5} rotationIntensity={0.1} floatIntensity={0.3}>
      <mesh ref={ref} position={position} scale={scale}>
        {getGeometry()}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.35}
          wireframe
          transparent
          opacity={0.2}
        />
      </mesh>
    </Float>
  );
}

// ─── Shape Data Type ──────────────────────────────────────────

interface ShapeData {
  id: number;
  geometry: 'ico' | 'octa' | 'dodeca' | 'torus' | 'tetra' | 'box';
  position: [number, number, number];
  color: string;
  speed: [number, number, number];
  scale: number;
}

// ─── Scene ────────────────────────────────────────────────────

function Scene({ isDark }: { isDark: boolean }) {
  const shapeId = useRef(100);
  const lastTap = useRef(0);
  const { camera, size } = useThree();

  const geometries: ('ico' | 'octa' | 'dodeca' | 'torus' | 'tetra' | 'box')[] = ['ico', 'octa', 'dodeca', 'torus', 'tetra', 'box'];

  const colors = isDark
    ? ['#00f0ff', '#bf00ff', '#00ff88', '#ff6b00', '#3b82f6', '#f472b6', '#fbbf24', '#6366f1']
    : ['#0891b2', '#7c3aed', '#059669', '#ea580c', '#2563eb', '#ec4899', '#f59e0b', '#4f46e5'];

  // Initial ambient shapes (evenly distributed top and bottom)
  const initialShapes: ShapeData[] = useMemo(() => {
    const items: ShapeData[] = [];
    for (let i = 0; i < 25; i++) {
      items.push({
        id: i,
        geometry: geometries[i % geometries.length]!,
        position: [
          (Math.random() - 0.5) * 18,
          (Math.random() - 0.5) * 12,
          -2 - Math.random() * 6,
        ],
        color: colors[i % colors.length]!,
        speed: [
          (Math.random() - 0.5) * 0.004,
          (Math.random() - 0.5) * 0.004,
          (Math.random() - 0.5) * 0.003,
        ],
        scale: 0.2 + Math.random() * 0.45,
      });
    }
    return items;
  }, []);

  const [spawnedShapes, setSpawnedShapes] = useState<ShapeData[]>([]);

  const handlePointerDown = useCallback((e: THREE.Event) => {
    const now = Date.now();
    const isDoubleTap = now - lastTap.current < 400;
    lastTap.current = now;

    if (!isDoubleTap) return;

    // Convert click to 3D position
    const ndc = new THREE.Vector2(
      ((e as unknown as { clientX: number }).clientX / size.width) * 2 - 1,
      -((e as unknown as { clientY: number }).clientY / size.height) * 2 + 1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(ndc, camera);
    const point = raycaster.ray.at(6, new THREE.Vector3());

    // Spawn 4-7 shapes that stay permanently
    const count = 4 + Math.floor(Math.random() * 4);
    const newShapes: ShapeData[] = [];

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2 + Math.random() * 0.5;
      const spread = 1 + Math.random() * 2;

      newShapes.push({
        id: shapeId.current++,
        geometry: geometries[Math.floor(Math.random() * geometries.length)]!,
        position: [
          point.x + Math.cos(angle) * spread,
          point.y + Math.sin(angle) * spread,
          point.z - Math.random() * 2,
        ],
        color: colors[Math.floor(Math.random() * colors.length)]!,
        speed: [
          (Math.random() - 0.5) * 0.006,
          (Math.random() - 0.5) * 0.006,
          (Math.random() - 0.5) * 0.004,
        ],
        scale: 0.2 + Math.random() * 0.4,
      });
    }

    // Keep max 50 spawned shapes (remove oldest if over)
    setSpawnedShapes(prev => [...prev, ...newShapes].slice(-50));
  }, [camera, size, colors, geometries]);

  return (
    <>
      <ambientLight intensity={isDark ? 0.1 : 0.3} />
      <pointLight position={[8, 8, 8]} intensity={isDark ? 0.25 : 0.15} color={isDark ? '#00f0ff' : '#0891b2'} />
      <pointLight position={[-8, -4, 4]} intensity={isDark ? 0.15 : 0.1} color={isDark ? '#bf00ff' : '#7c3aed'} />

      {/* Invisible click detection plane */}
      <mesh visible={false} onPointerDown={handlePointerDown}>
        <planeGeometry args={[50, 50]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>

      {/* Initial ambient shapes (always present) */}
      {initialShapes.map(s => (
        <FloatingShape
          key={s.id}
          geometry={s.geometry}
          position={s.position}
          color={s.color}
          speed={s.speed}
          scale={s.scale}
        />
      ))}

      {/* Spawned shapes from double-tap (permanent, float forever) */}
      {spawnedShapes.map(s => (
        <FloatingShape
          key={s.id}
          geometry={s.geometry}
          position={s.position}
          color={s.color}
          speed={s.speed}
          scale={s.scale}
        />
      ))}
    </>
  );
}

// ─── Main Export ──────────────────────────────────────────────

export default function InteractiveBackground({ className = '' }: { className?: string }) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  return (
    <div className={`pointer-events-auto absolute inset-0 overflow-hidden ${className}`} style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 10], fov: 60 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent', pointerEvents: 'auto' }}
      >
        <Scene isDark={isDark} />
      </Canvas>
    </div>
  );
}

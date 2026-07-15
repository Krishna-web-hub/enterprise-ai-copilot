/**
 * FloatingHologram Component
 *
 * 3D rotating geometric wireframe shapes that float in the background:
 * - Icosahedron, octahedron, and dodecahedron wireframes
 * - Slow rotation at different speeds and axes
 * - Translucent neon glow materials
 * - Used as a subtle background layer in the main layout
 */

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';

function WireframeShape({
  geometry,
  position,
  color,
  rotationSpeed,
  scale = 1,
}: {
  geometry: 'icosahedron' | 'octahedron' | 'dodecahedron' | 'torus';
  position: [number, number, number];
  color: string;
  rotationSpeed: [number, number, number];
  scale?: number;
}) {
  const ref = useRef<THREE.Mesh>(null!);

  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.x += rotationSpeed[0];
      ref.current.rotation.y += rotationSpeed[1];
      ref.current.rotation.z += rotationSpeed[2];
    }
  });

  const getGeometry = () => {
    switch (geometry) {
      case 'icosahedron':
        return <icosahedronGeometry args={[1, 0]} />;
      case 'octahedron':
        return <octahedronGeometry args={[1, 0]} />;
      case 'dodecahedron':
        return <dodecahedronGeometry args={[1, 0]} />;
      case 'torus':
        return <torusGeometry args={[1, 0.3, 8, 16]} />;
    }
  };

  return (
    <Float speed={1} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={ref} position={position} scale={scale}>
        {getGeometry()}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.5}
          wireframe
          transparent
          opacity={0.3}
        />
      </mesh>
    </Float>
  );
}

function HologramScene() {
  return (
    <>
      <ambientLight intensity={0.1} />
      <pointLight position={[10, 10, 10]} intensity={0.3} color="#00f0ff" />
      <pointLight position={[-10, -10, 5]} intensity={0.2} color="#bf00ff" />

      {/* Scattered wireframe shapes */}
      <WireframeShape
        geometry="icosahedron"
        position={[-4, 2, -5]}
        color="#00f0ff"
        rotationSpeed={[0.002, 0.003, 0.001]}
        scale={0.8}
      />
      <WireframeShape
        geometry="octahedron"
        position={[4, -1, -4]}
        color="#bf00ff"
        rotationSpeed={[-0.001, 0.002, -0.003]}
        scale={0.6}
      />
      <WireframeShape
        geometry="dodecahedron"
        position={[-2, -3, -6]}
        color="#00ff88"
        rotationSpeed={[0.003, -0.001, 0.002]}
        scale={0.5}
      />
      <WireframeShape
        geometry="torus"
        position={[3, 3, -7]}
        color="#00f0ff"
        rotationSpeed={[0.001, 0.002, -0.001]}
        scale={0.7}
      />
      <WireframeShape
        geometry="icosahedron"
        position={[5, -3, -8]}
        color="#bf00ff"
        rotationSpeed={[-0.002, 0.001, 0.003]}
        scale={0.4}
      />
    </>
  );
}

interface FloatingHologramProps {
  className?: string;
}

export default function FloatingHologram({ className = '' }: FloatingHologramProps) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 8], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent', pointerEvents: 'none' }}
      >
        <HologramScene />
      </Canvas>
    </div>
  );
}

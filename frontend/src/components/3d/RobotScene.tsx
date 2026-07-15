/**
 * RobotScene Component
 *
 * A 3D AI Core visualization using React Three Fiber:
 * - Central glowing sphere (the "brain")
 * - Orbiting rings with different rotation speeds
 * - Floating particles around the core
 * - Pulsating light effects
 * - Mouse-responsive rotation
 */

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Sphere, Torus, Stars } from '@react-three/drei';
import * as THREE from 'three';

/** The central AI core sphere with distort material */
function CoreSphere() {
  const meshRef = useRef<THREE.Mesh>(null!);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
      meshRef.current.rotation.y += 0.003;
    }
  });

  return (
    <Sphere ref={meshRef} args={[1, 64, 64]}>
      <MeshDistortMaterial
        color="#00f0ff"
        emissive="#00f0ff"
        emissiveIntensity={0.4}
        roughness={0.2}
        metalness={0.8}
        distort={0.3}
        speed={2}
        transparent
        opacity={0.9}
      />
    </Sphere>
  );
}

/** Orbiting ring */
function OrbitRing({ radius, speed, tilt, color }: { radius: number; speed: number; tilt: number; color: string }) {
  const ref = useRef<THREE.Mesh>(null!);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.z = state.clock.elapsedTime * speed;
      ref.current.rotation.x = tilt;
    }
  });

  return (
    <Torus ref={ref} args={[radius, 0.015, 16, 100]}>
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.8}
        transparent
        opacity={0.6}
      />
    </Torus>
  );
}

/** Small floating particles orbiting the core */
function OrbitalParticles({ count = 80 }: { count?: number }) {
  const points = useRef<THREE.Points>(null!);

  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.5 + Math.random() * 1.5;
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    return pos;
  }, [count]);

  useFrame((state) => {
    if (points.current) {
      points.current.rotation.y = state.clock.elapsedTime * 0.1;
      points.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.05) * 0.2;
    }
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#00f0ff"
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  );
}

/** Inner glow shell */
function GlowShell() {
  const ref = useRef<THREE.Mesh>(null!);

  useFrame((state) => {
    if (ref.current) {
      const scale = 1.2 + Math.sin(state.clock.elapsedTime * 2) * 0.05;
      ref.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <Sphere ref={ref} args={[1.1, 32, 32]}>
      <meshStandardMaterial
        color="#00f0ff"
        emissive="#00f0ff"
        emissiveIntensity={0.2}
        transparent
        opacity={0.1}
        side={THREE.BackSide}
      />
    </Sphere>
  );
}

/** The complete 3D scene */
function Scene() {
  const groupRef = useRef<THREE.Group>(null!);

  useFrame((state) => {
    if (groupRef.current) {
      // Gentle floating motion
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.1;
      // Subtle mouse follow
      const mouseX = state.mouse.x * 0.3;
      const mouseY = state.mouse.y * 0.2;
      groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, mouseX, 0.05);
      groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, -mouseY, 0.05);
    }
  });

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.2} />
      <pointLight position={[5, 5, 5]} intensity={1} color="#00f0ff" />
      <pointLight position={[-5, -5, 3]} intensity={0.5} color="#bf00ff" />
      <pointLight position={[0, 0, 5]} intensity={0.3} color="#ffffff" />

      {/* Background stars */}
      <Stars radius={50} depth={50} count={1000} factor={2} saturation={0} fade speed={0.5} />

      {/* Main group */}
      <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5}>
        <group ref={groupRef}>
          {/* Core */}
          <CoreSphere />
          <GlowShell />

          {/* Orbiting rings */}
          <OrbitRing radius={1.6} speed={0.5} tilt={Math.PI / 4} color="#00f0ff" />
          <OrbitRing radius={1.9} speed={-0.3} tilt={Math.PI / 3} color="#bf00ff" />
          <OrbitRing radius={2.2} speed={0.2} tilt={Math.PI / 6} color="#00ff88" />

          {/* Particles */}
          <OrbitalParticles count={100} />
        </group>
      </Float>
    </>
  );
}

interface RobotSceneProps {
  className?: string;
}

export default function RobotScene({ className = '' }: RobotSceneProps) {
  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 45 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <Scene />
      </Canvas>
    </div>
  );
}

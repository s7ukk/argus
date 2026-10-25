import React, { useEffect, useRef } from 'react';

interface StarburnCoreProps {
  isListening: boolean;
  isSpeaking: boolean;
  size?: number;
}

export const StarburnCore: React.FC<StarburnCoreProps> = ({
  isListening,
  isSpeaking,
  size = 180,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let angle = 0;
    let pulse = 0;

    // Dust particles
    const particleCount = 28;
    const particles = Array.from({ length: particleCount }, () => ({
      angle: Math.random() * Math.PI * 2,
      dist: 22 + Math.random() * 56,
      speed: 0.005 + Math.random() * 0.012,
      radius: 0.8 + Math.random() * 1.6,
      alpha: 0.2 + Math.random() * 0.6,
    }));

    const render = () => {
      ctx.clearRect(0, 0, size, size);
      const cx = size / 2;
      const cy = size / 2;

      angle += 0.016;
      pulse += 0.032;

      const dynamicAmp = isSpeaking
        ? 1 + Math.sin(pulse * 3.5) * 0.16
        : isListening
        ? 1 + Math.sin(pulse * 2.2) * 0.1
        : 1 + Math.sin(pulse) * 0.035;

      // 1. Nebula Cosmic Cloud Glow (Pure Silver/Monochrome or red/gold when active)
      const nebula = ctx.createRadialGradient(cx, cy, 10, cx, cy, (size / 2) * dynamicAmp);
      if (isListening) {
        nebula.addColorStop(0, 'rgba(239, 68, 68, 0.45)');
        nebula.addColorStop(0.4, 'rgba(220, 38, 38, 0.2)');
        nebula.addColorStop(0.8, 'rgba(255, 255, 255, 0.04)');
        nebula.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else if (isSpeaking) {
        nebula.addColorStop(0, 'rgba(245, 158, 11, 0.55)');
        nebula.addColorStop(0.3, 'rgba(239, 68, 68, 0.35)');
        nebula.addColorStop(0.7, 'rgba(255, 255, 255, 0.08)');
        nebula.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        nebula.addColorStop(0, 'rgba(255, 255, 255, 0.18)');
        nebula.addColorStop(0.45, 'rgba(226, 232, 240, 0.08)');
        nebula.addColorStop(0.8, 'rgba(255, 255, 255, 0.03)');
        nebula.addColorStop(1, 'rgba(0, 0, 0, 0)');
      }

      ctx.fillStyle = nebula;
      ctx.beginPath();
      ctx.arc(cx, cy, (size / 2) * 0.95, 0, Math.PI * 2);
      ctx.fill();

      // 2. Celestial Dust Particles
      particles.forEach((p) => {
        p.angle += p.speed;
        const px = cx + Math.cos(p.angle) * p.dist * dynamicAmp;
        const py = cy + Math.sin(p.angle) * p.dist * dynamicAmp;
        ctx.fillStyle = isListening
          ? `rgba(254, 202, 202, ${p.alpha})`
          : isSpeaking
          ? `rgba(253, 230, 138, ${p.alpha})`
          : `rgba(241, 245, 249, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(px, py, p.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // 3. Starburn Outer Orbital Ring
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angle);
      ctx.beginPath();
      ctx.arc(0, 0, 78 * dynamicAmp, 0, Math.PI * 2);
      ctx.strokeStyle = isListening
        ? 'rgba(239, 68, 68, 0.75)'
        : isSpeaking
        ? 'rgba(245, 158, 11, 0.8)'
        : 'rgba(255, 255, 255, 0.45)';
      ctx.lineWidth = 1.4;
      ctx.setLineDash([12, 16, 3, 12]);
      ctx.stroke();
      ctx.restore();

      // 4. Counter-rotating Plasma Ring
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(-angle * 1.5);
      ctx.beginPath();
      ctx.arc(0, 0, 58 * dynamicAmp, 0, Math.PI * 2);
      ctx.strokeStyle = isListening
        ? 'rgba(252, 165, 165, 0.7)'
        : isSpeaking
        ? 'rgba(253, 230, 138, 0.75)'
        : 'rgba(203, 213, 225, 0.55)';
      ctx.lineWidth = 1.2;
      ctx.setLineDash([6, 10, 18, 6]);
      ctx.stroke();
      ctx.restore();

      // 5. Starburn Radiant Rays (8 celestial flares)
      const rayCount = 8;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angle * 0.5);
      for (let i = 0; i < rayCount; i++) {
        const theta = (i / rayCount) * Math.PI * 2;
        const rayLen = (36 + (i % 2 === 0 ? 18 : 6)) * dynamicAmp;
        const rx = Math.cos(theta) * rayLen;
        const ry = Math.sin(theta) * rayLen;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(rx, ry);
        ctx.strokeStyle = isListening
          ? 'rgba(239, 68, 68, 0.85)'
          : isSpeaking
          ? 'rgba(245, 158, 11, 0.9)'
          : 'rgba(255, 255, 255, 0.6)';
        ctx.lineWidth = i % 2 === 0 ? 1.8 : 1;
        ctx.stroke();
      }
      ctx.restore();

      // 6. Supernova Core Orb
      const coreGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, 26 * dynamicAmp);
      coreGrad.addColorStop(0, '#ffffff');
      coreGrad.addColorStop(0.3, isListening ? '#f87171' : isSpeaking ? '#fde047' : '#e2e8f0');
      coreGrad.addColorStop(0.7, isListening ? '#dc2626' : isSpeaking ? '#f59e0b' : '#64748b');
      coreGrad.addColorStop(1, '#09090b');

      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, 24 * dynamicAmp, 0, Math.PI * 2);
      ctx.fill();

      // Core bright center point
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(cx, cy, 6 * dynamicAmp, 0, Math.PI * 2);
      ctx.fill();

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [isListening, isSpeaking, size]);

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        userSelect: 'none',
        pointerEvents: 'none',
      }}
    >
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{ width: size, height: size }}
      />
    </div>
  );
};

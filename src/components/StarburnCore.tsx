import React, { useEffect, useRef } from 'react';

interface StarburnCoreProps {
  isListening: boolean;
  isSpeaking: boolean;
  size?: number;
}

interface Particle {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  speed: number;
  angle: number;
  dist: number;
}

export const StarburnCore: React.FC<StarburnCoreProps> = ({
  isListening,
  isSpeaking,
  size = 240
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let angle = 0;
    let pulse = 0;

    // Generate orbiting celestial dust particles
    const particleCount = 42;
    const particles: Particle[] = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: 0,
        y: 0,
        radius: Math.random() * 1.8 + 0.6,
        alpha: Math.random() * 0.7 + 0.3,
        speed: (Math.random() * 0.015 + 0.005) * (Math.random() > 0.5 ? 1 : -1),
        angle: Math.random() * Math.PI * 2,
        dist: Math.random() * (size * 0.42) + 20
      });
    }

    const render = () => {
      ctx.clearRect(0, 0, size, size);
      const cx = size / 2;
      const cy = size / 2;

      angle += 0.018;
      pulse += 0.035;

      const dynamicAmp = isSpeaking
        ? 1 + Math.sin(pulse * 3.5) * 0.16
        : isListening
        ? 1 + Math.sin(pulse * 2.2) * 0.1
        : 1 + Math.sin(pulse) * 0.035;

      // 1. Nebula Cosmic Cloud Glow
      const nebula = ctx.createRadialGradient(cx, cy, 10, cx, cy, (size / 2) * dynamicAmp);
      if (isListening) {
        nebula.addColorStop(0, 'rgba(244, 63, 94, 0.45)');
        nebula.addColorStop(0.4, 'rgba(225, 29, 72, 0.2)');
        nebula.addColorStop(0.8, 'rgba(168, 85, 247, 0.08)');
        nebula.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else if (isSpeaking) {
        nebula.addColorStop(0, 'rgba(251, 191, 36, 0.55)');
        nebula.addColorStop(0.3, 'rgba(244, 63, 94, 0.35)');
        nebula.addColorStop(0.7, 'rgba(168, 85, 247, 0.18)');
        nebula.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        nebula.addColorStop(0, 'rgba(168, 85, 247, 0.35)');
        nebula.addColorStop(0.45, 'rgba(124, 58, 237, 0.16)');
        nebula.addColorStop(0.8, 'rgba(56, 189, 248, 0.05)');
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
          ? `rgba(253, 164, 175, ${p.alpha})`
          : isSpeaking
          ? `rgba(253, 230, 138, ${p.alpha})`
          : `rgba(216, 180, 254, ${p.alpha})`;
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
        ? 'rgba(244, 63, 94, 0.75)'
        : isSpeaking
        ? 'rgba(251, 191, 36, 0.8)'
        : 'rgba(168, 85, 247, 0.55)';
      ctx.lineWidth = 1.6;
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
        ? 'rgba(251, 113, 133, 0.7)'
        : 'rgba(192, 132, 252, 0.65)';
      ctx.lineWidth = 1.4;
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
          ? 'rgba(244, 63, 94, 0.85)'
          : isSpeaking
          ? 'rgba(251, 191, 36, 0.9)'
          : 'rgba(232, 121, 249, 0.75)';
        ctx.lineWidth = i % 2 === 0 ? 2 : 1;
        ctx.stroke();
      }
      ctx.restore();

      // 6. Supernova Core Orb
      const coreGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, 26 * dynamicAmp);
      coreGrad.addColorStop(0, '#ffffff');
      coreGrad.addColorStop(0.3, isListening ? '#f43f5e' : isSpeaking ? '#fbbf24' : '#c084fc');
      coreGrad.addColorStop(0.7, isListening ? '#be123c' : isSpeaking ? '#e11d48' : '#7c3aed');
      coreGrad.addColorStop(1, '#3b0764');

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
    <div className="relative flex items-center justify-center select-none pointer-events-none">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        className="drop-shadow-[0_0_40px_rgba(168,85,247,0.45)]"
      />
    </div>
  );
};

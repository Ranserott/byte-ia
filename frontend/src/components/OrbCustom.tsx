"use client";

import { useEffect, useRef } from "react";

/**
 * High-level state of the assistant, used to pick the orb color.
 *
 * - ``idle``       — passive / waiting for a wake word.
 * - ``listening``  — the mic is open and capturing audio.
 * - ``thinking``   — the LLM is processing a request.
 * - ``speaking``   — TTS is playing back the response.
 */
export type OrbState = "idle" | "listening" | "thinking" | "speaking";

export interface OrbCustomProps {
  /** Current assistant state. Drives the orb color. */
  state: OrbState;
  /** Inner diameter (CSS pixels) of the orb before the 1.2x breathing scale. */
  size?: number;
  /**
   * Normalized audio level (0..1) used to react the orb to mic / playback
   * amplitude. Defaults to ``0`` so the orb just breathes.
   */
  audioLevel?: number;
  /**
   * Override the default color palette. Keys missing from the map fall back
   * to the bundled defaults.
   */
  colors?: Partial<Record<OrbState, string>>;
}

/**
 * Default color palette (terracotta + traffic-light accents).
 *
 * Override per-instance with the ``colors`` prop or globally by patching
 * this constant before mounting. All values are hex strings in ``#rrggbb``
 * form (no transparency — the canvas adds the alpha channel).
 */
export const ORB_DEFAULT_COLORS: Record<OrbState, string> = {
  idle: "#f54a00",        // terracotta orange (default)
  listening: "#06b6d4",   // cyan
  thinking: "#eab308",    // amber
  speaking: "#10b981",    // emerald
};

/** Compose a user-supplied color map on top of the defaults. */
function resolveColors(
  overrides: Partial<Record<OrbState, string>> | undefined,
): Record<OrbState, string> {
  return { ...ORB_DEFAULT_COLORS, ...(overrides ?? {}) };
}

/**
 * ``OrbCustom`` is a canvas-rendered, fully animated orb that reacts to the
 * assistant state and the current audio level. It is intentionally self
 * contained: no animation libraries, no Tailwind, no external SVG assets.
 *
 * The component owns a single ``requestAnimationFrame`` loop that redraws
 * the radial gradient every frame; the loop is cancelled on unmount or when
 * its dependencies change, so unmounting does not leak frames.
 *
 * @example
 *   ```tsx
 *   import { OrbCustom } from "@/components/OrbCustom";
 *
 *   <OrbCustom state="listening" audioLevel={micLevel} size={240} />
 *   ```
 */
export function OrbCustom({
  state,
  size = 240,
  audioLevel = 0,
  colors,
}: OrbCustomProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const palette = resolveColors(colors);
  const baseColor = palette[state];
  // 1.2x scale on top of the requested size — gives the glow enough
  // breathing room without changing the perceived "diameter" of the core.
  const scaledSize = Math.round(size * 1.2);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let t = 0;

    function draw() {
      t += 0.016;
      const breath = Math.sin(t * 0.6) * 0.04;
      // Audio reaction is intentionally pronounced (max +35%) so the orb
      // visibly pulses when someone speaks.
      const audioScale = 1 + Math.max(0, Math.min(1, audioLevel)) * 0.35;
      const r = (scaledSize / 2) * (1 + breath) * audioScale;

      // Transparent background — let the parent show through.
      ctx!.clearRect(0, 0, scaledSize, scaledSize);

      // Outer halo glow.
      const halo = ctx!.createRadialGradient(
        scaledSize / 2, scaledSize / 2, r * 0.1,
        scaledSize / 2, scaledSize / 2, r * 1.5,
      );
      halo.addColorStop(0, baseColor + "FF");
      halo.addColorStop(0.4, baseColor + "60");
      halo.addColorStop(1, baseColor + "00");
      ctx!.fillStyle = halo;
      ctx!.fillRect(0, 0, scaledSize, scaledSize);

      // Solid core circle.
      const core = ctx!.createRadialGradient(
        scaledSize / 2, scaledSize / 2, 0,
        scaledSize / 2, scaledSize / 2, r * 0.5,
      );
      core.addColorStop(0, baseColor);
      core.addColorStop(0.7, baseColor + "80");
      core.addColorStop(1, baseColor + "00");
      ctx!.fillStyle = core;
      ctx!.beginPath();
      ctx!.arc(scaledSize / 2, scaledSize / 2, r * 0.5, 0, Math.PI * 2);
      ctx!.fill();

      raf = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(raf);
  }, [baseColor, scaledSize, audioLevel]);

  return (
    <div
      style={{
        width: scaledSize,
        height: scaledSize,
        position: "relative",
        margin: "0 auto",
      }}
      aria-label={`Assistant orb — ${state}`}
      role="img"
    >
      <canvas
        ref={canvasRef}
        width={scaledSize}
        height={scaledSize}
        data-state={state}
      />
    </div>
  );
}

export default OrbCustom;

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TrainerDrawingConfig } from "@/lib/api";

type Point = { x: number; y: number };
type TextLabel = { x: number; y: number; text: string };

type Props = {
  config: TrainerDrawingConfig;
  prompt?: string;
  busy: boolean;
  completed: boolean;
  onComplete: () => void;
};

function drawExampleSketch(ctx: CanvasRenderingContext2D, width: number, height: number) {
  ctx.save();
  ctx.globalAlpha = 0.28;
  ctx.strokeStyle = "#475569";
  ctx.fillStyle = "#64748b";
  ctx.lineWidth = 2;
  const baseY = height * 0.72;
  ctx.beginPath();
  ctx.arc(width * 0.28, baseY - 36, 10, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(width * 0.28, baseY - 26);
  ctx.lineTo(width * 0.28, baseY);
  ctx.moveTo(width * 0.28, baseY - 18);
  ctx.lineTo(width * 0.18, baseY - 4);
  ctx.moveTo(width * 0.28, baseY - 18);
  ctx.lineTo(width * 0.38, baseY - 4);
  ctx.moveTo(width * 0.28, baseY);
  ctx.lineTo(width * 0.2, baseY + 18);
  ctx.moveTo(width * 0.28, baseY);
  ctx.lineTo(width * 0.36, baseY + 18);
  ctx.stroke();
  const fireX = width * 0.58;
  const fireY = baseY - 8;
  ctx.fillStyle = "#f97316";
  ctx.beginPath();
  ctx.moveTo(fireX, fireY - 42);
  ctx.lineTo(fireX + 18, fireY);
  ctx.lineTo(fireX - 18, fireY);
  ctx.closePath();
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(fireX + 28, fireY - 28);
  ctx.lineTo(fireX + 40, fireY + 4);
  ctx.lineTo(fireX + 16, fireY + 4);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#78350f";
  ctx.beginPath();
  ctx.moveTo(fireX - 8, fireY + 4);
  ctx.lineTo(fireX + 8, fireY + 4);
  ctx.lineTo(fireX + 6, fireY + 22);
  ctx.lineTo(fireX - 6, fireY + 22);
  ctx.closePath();
  ctx.stroke();
  ctx.restore();
}

function drawLandscape(ctx: CanvasRenderingContext2D, width: number, height: number, showExample: boolean) {
  const sky = ctx.createLinearGradient(0, 0, 0, height);
  sky.addColorStop(0, "#b8d4f0");
  sky.addColorStop(1, "#e8f0fa");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#6b9b6b";
  ctx.beginPath();
  ctx.moveTo(0, height * 0.78);
  ctx.quadraticCurveTo(width * 0.25, height * 0.68, width * 0.5, height * 0.74);
  ctx.quadraticCurveTo(width * 0.78, height * 0.8, width, height * 0.72);
  ctx.lineTo(width, height);
  ctx.lineTo(0, height);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "rgba(74, 144, 226, 0.45)";
  ctx.fillRect(0, height * 0.82, width, height * 0.18);
  if (showExample) {
    drawExampleSketch(ctx, width, height);
  }
}

export function DrawingCanvas({ config, prompt, busy, completed, onComplete }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inkRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const drawingRef = useRef(false);
  const lastPointRef = useRef<Point | null>(null);
  const [tool, setTool] = useState<"pen" | "eraser">("pen");
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null);
  const [labels, setLabels] = useState<TextLabel[]>([]);
  const [size, setSize] = useState({ width: 640, height: 420 });

  const terms = config.terms || [];
  const showExample = /feuer|nahrung|koch|zubereit|braten|grill|flamm/i.test(
    `${prompt || ""} ${config.title || ""}`,
  );

  const composite = useCallback(() => {
    const canvas = canvasRef.current;
    const ink = inkRef.current;
    if (!canvas || !ink) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawLandscape(ctx, canvas.width, canvas.height, showExample);
    ctx.drawImage(ink, 0, 0);
    ctx.font = "bold 14px system-ui, sans-serif";
    ctx.textBaseline = "middle";
    for (const label of labels) {
      const padding = 6;
      const metrics = ctx.measureText(label.text);
      const boxW = metrics.width + padding * 2;
      const boxH = 22;
      ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
      ctx.strokeStyle = "#2c5282";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(label.x, label.y - boxH / 2, boxW, boxH, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#1a365d";
      ctx.fillText(label.text, label.x + padding, label.y);
    }
  }, [labels, showExample]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new ResizeObserver(() => {
      const width = Math.min(720, Math.max(320, node.clientWidth));
      const height = Math.round(width * 0.65);
      setSize({ width, height });
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = size.width;
    canvas.height = size.height;
    const ink = document.createElement("canvas");
    ink.width = size.width;
    ink.height = size.height;
    inkRef.current = ink;
    composite();
  }, [size, composite]);

  useEffect(() => {
    composite();
  }, [labels, composite]);

  function canvasPoint(event: React.PointerEvent<HTMLCanvasElement>): Point {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (event.clientX - rect.left) * scaleX,
      y: (event.clientY - rect.top) * scaleY,
    };
  }

  function strokeLine(from: Point, to: Point, pressure: number) {
    const ink = inkRef.current;
    if (!ink) return;
    const ctx = ink.getContext("2d");
    if (!ctx) return;
    const width = tool === "eraser" ? 18 : Math.max(2, pressure * 5);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = tool === "eraser" ? "#000000" : "#1a1a1a";
    ctx.globalCompositeOperation = tool === "eraser" ? "destination-out" : "source-over";
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
    ctx.globalCompositeOperation = "source-over";
  }

  function onPointerDown(event: React.PointerEvent<HTMLCanvasElement>) {
    if (completed || busy) return;
    const point = canvasPoint(event);
    if (selectedTerm) {
      setLabels((prev) => [...prev, { x: point.x, y: point.y, text: selectedTerm }]);
      setSelectedTerm(null);
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    lastPointRef.current = point;
    strokeLine(point, point, event.pressure || 0.5);
    composite();
  }

  function onPointerMove(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawingRef.current || completed || busy) return;
    const point = canvasPoint(event);
    const last = lastPointRef.current;
    if (!last) return;
    strokeLine(last, point, event.pressure || 0.5);
    lastPointRef.current = point;
    composite();
  }

  function onPointerUp(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    lastPointRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function clearDrawing() {
    if (completed || busy) return;
    const ink = inkRef.current;
    const ctx = ink?.getContext("2d");
    if (ink && ctx) {
      ctx.clearRect(0, 0, ink.width, ink.height);
    }
    setLabels([]);
    composite();
  }

  function downloadPng() {
    composite();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `${(config.title || "zeichnung").replace(/\s+/g, "-").toLowerCase()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function printDrawing() {
    composite();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(
      `<html><head><title>${config.title || "Zeichnung"}</title></head><body style="margin:0;text-align:center">` +
        `<img src="${dataUrl}" style="max-width:100%;height:auto" onload="window.print();window.close()" />` +
        `</body></html>`,
    );
    win.document.close();
  }

  return (
    <div className="drawing-canvas-exercise stack">
      {config.title && <h4 className="drawing-canvas-title">{config.title}</h4>}
      {showExample && (
        <p className="muted drawing-example-hint">
          Die graue Skizze ist nur ein Beispiel — zeichne und beschrifte deine eigene Szene (Feuer, Nahrung,
          Menschen …).
        </p>
      )}
      <p className="muted">
        Mit dem Stift zeichnen. Optional: Begriff antippen, dann auf die Zeichnung tippen zum Beschriften.
      </p>
      <div className="drawing-toolbar">
        <button
          type="button"
          className={tool === "pen" ? "trainer-tab active" : "trainer-tab"}
          disabled={completed || busy}
          onClick={() => setTool("pen")}
        >
          Stift
        </button>
        <button
          type="button"
          className={tool === "eraser" ? "trainer-tab active" : "trainer-tab"}
          disabled={completed || busy}
          onClick={() => setTool("eraser")}
        >
          Radierer
        </button>
        <button type="button" className="ghost" disabled={completed || busy} onClick={clearDrawing}>
          Leeren
        </button>
        <button type="button" className="ghost" onClick={downloadPng}>
          PNG speichern
        </button>
        <button type="button" className="ghost" onClick={printDrawing}>
          Drucken
        </button>
      </div>
      {terms.length > 0 && (
        <div className="label-diagram-terms" role="listbox" aria-label="Begriffe zum Beschriften">
          {terms.map((term) => (
            <button
              key={term}
              type="button"
              className={`label-diagram-term${selectedTerm === term ? " selected" : ""}`}
              disabled={completed || busy}
              onClick={() => setSelectedTerm(selectedTerm === term ? null : term)}
            >
              {term}
            </button>
          ))}
        </div>
      )}
      <div ref={containerRef} className="drawing-canvas-wrap">
        <canvas
          ref={canvasRef}
          className="drawing-canvas"
          style={{ touchAction: "none" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        />
      </div>
      {!completed && (
        <div className="learn-actions">
          <button type="button" className="btn-primary" disabled={busy} onClick={onComplete}>
            Fertig — Aufgabe abschliessen
          </button>
        </div>
      )}
      {completed && (
        <p className="quiz-verdict ok">Zeichnung gespeichert — du kannst sie ausdrucken oder als PNG mitnehmen.</p>
      )}
    </div>
  );
}

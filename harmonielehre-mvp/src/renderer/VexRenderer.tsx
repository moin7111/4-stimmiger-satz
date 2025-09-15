import React, { useEffect, useRef } from "react";
import { Flow } from "vexflow";

export default function VexRenderer({ notes }: { notes: { S?: string; A?: string; T?: string; B?: string } }) {
  const containerRef = useRef(null as any);

  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.innerHTML = "";
    const renderer = new Flow.Renderer(containerRef.current, Flow.Renderer.Backends.SVG);
    const width = 800;
    const height = 240;
    renderer.resize(width, height);
    const context = renderer.getContext();

    const staveY = { S: 10, A: 70, T: 130, B: 190 } as const;
    const clefs = { S: "treble", A: "treble", T: "treble", B: "bass" } as const;

    (Object.keys(staveY) as (keyof typeof staveY)[]).forEach((voice) => {
      const stave = new Flow.Stave(10, staveY[voice], width - 20);
      stave.addClef(clefs[voice]);
      stave.setContext(context).draw();
      const noteName = (notes as any)[voice] ?? "b/4"; // placeholder rests as B4
      const staveNote = new Flow.StaveNote({ keys: [noteName], duration: "q" });
      const voiceObj = new Flow.Voice({ num_beats: 1, beat_value: 4 }).addTickables([staveNote]);
      new Flow.Formatter().joinVoices([voiceObj]).format([voiceObj], width - 80);
      voiceObj.draw(context, stave);
    });
  }, [notes]);

  return <div ref={containerRef} />;
}


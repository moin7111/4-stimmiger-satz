import { ChordSpec, KeyContext } from "./types";

// Map note names to pitch classes (C=0)
const NOTE_TO_PC: Record<string, number> = {
  C: 0,
  "B#": 0,
  "C#": 1,
  Db: 1,
  D: 2,
  "D#": 3,
  Eb: 3,
  E: 4,
  Fb: 4,
  "E#": 5,
  F: 5,
  "F#": 6,
  Gb: 6,
  G: 7,
  "G#": 8,
  Ab: 8,
  A: 9,
  "A#": 10,
  Bb: 10,
  B: 11,
  Cb: 11,
};

export function noteNameToPc(name: string): number {
  const k = name.trim();
  if (!(k in NOTE_TO_PC)) throw new Error(`Unknown key or note: ${name}`);
  return NOTE_TO_PC[k];
}

// Scale degrees for major and harmonic minor as pitch classes from tonic 0
const MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11];
const HARM_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 11]; // raised 7th

function scalePc(ctx: KeyContext, degree: number): number {
  const tonic = noteNameToPc(ctx.key);
  const scale = ctx.mode === "major" ? MAJOR_SCALE : HARM_MINOR_SCALE;
  const idx = ((degree - 1) % 7 + 7) % 7;
  return (tonic + scale[idx]) % 12;
}

export function functionToChord(ctx: KeyContext, func: string): ChordSpec {
  switch (func) {
    case "T": {
      const pcs = [1, 3, 5].map((d) => scalePc(ctx, d));
      return { pitchClasses: unique(pcs), isSeventh: false };
    }
    case "TP": {
      const degree = ctx.mode === "major" ? 6 : 3;
      const pcs = [degree, ((degree + 2 - 1) % 7) + 1, ((degree + 4 - 1) % 7) + 1].map((d) =>
        scalePc(ctx, d)
      );
      return { pitchClasses: unique(pcs), isSeventh: false };
    }
    case "S": {
      const pcs = [4, 6, 1].map((d) => scalePc(ctx, d));
      return { pitchClasses: unique(pcs), isSeventh: false };
    }
    case "D": {
      const pcs = [5, 7, 2].map((d) => scalePc(ctx, d));
      return { pitchClasses: unique(pcs), isSeventh: false };
    }
    case "D7": {
      const pcs = [5, 7, 2, 4].map((d) => scalePc(ctx, d));
      return { pitchClasses: unique(pcs), isSeventh: true };
    }
    case "DD": {
      // V of V
      // In major: V is degree 5, so V/V is built on its dominant: degree 2
      const pcs = [2, 4, 6].map((d) => scalePc({ key: ctx.key, mode: "major" }, d));
      return { pitchClasses: unique(pcs), isSeventh: false };
    }
    case "DD7": {
      const pcs = [2, 4, 6, 1].map((d) => scalePc({ key: ctx.key, mode: "major" }, d));
      return { pitchClasses: unique(pcs), isSeventh: true };
    }
    default:
      throw new Error(`Unsupported function: ${func}`);
  }
}

function unique(arr: number[]): number[] {
  return [...new Set(arr)].sort((a, b) => a - b);
}


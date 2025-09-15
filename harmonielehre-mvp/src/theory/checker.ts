import { CheckIssue, FunctionToken, KeyContext, SATBVoicing } from "./types";
import { functionToChord } from "./key";

export function checkParallels(prev: SATBVoicing, next: SATBVoicing): CheckIssue[] {
  const parts: (keyof SATBVoicing)[] = ["S", "A", "T", "B"];
  const combos: [keyof SATBVoicing, keyof SATBVoicing][] = [];
  for (let i = 0; i < parts.length; i++) {
    for (let j = i + 1; j < parts.length; j++) combos.push([parts[i], parts[j]]);
  }
  const issues: CheckIssue[] = [];
  for (const [p1, p2] of combos) {
    const a1 = prev[p1];
    const a2 = prev[p2];
    const b1 = next[p1];
    const b2 = next[p2];
    const intA = intervalClass(a1, a2);
    const intB = intervalClass(b1, b2);
    const dir1 = Math.sign(b1 - a1);
    const dir2 = Math.sign(b2 - a2);
    if ((intA === 7 || intA === 12) && (intB === 7 || intB === 12) && dir1 === dir2 && dir1 !== 0) {
      issues.push({ type: "parallel", message: `Parallele reine Intervalle zwischen ${p1} und ${p2}`, parts: [p1, p2] });
    }
  }
  return issues;
}

export function checkRangesAndCrossing(v: SATBVoicing): CheckIssue[] {
  const issues: CheckIssue[] = [];
  if (!(v.S > v.A && v.A > v.T && v.T > v.B)) {
    issues.push({ type: "crossing", message: "Stimmkreuzung / Überlappung erkannt" });
  }
  return issues;
}

function intervalClass(a: number, b: number): number {
  const d = Math.abs(b - a);
  // map any compound to simple class: keep as is to spot 7 (P5) and 12 (P8)
  if (d >= 24) return d % 12 === 0 ? 12 : d % 12 === 7 ? 7 : d % 12; // coarse
  return d;
}

export function checkInversionRequirement(token: FunctionToken, ctx: KeyContext, v: SATBVoicing): CheckIssue[] {
  if (!token.inversion) return [];
  const chord = functionToChord(ctx, token.func);
  let requiredPc: number | null = null;
  if (token.inversion === "6/4") requiredPc = chord.pitchClasses[2];
  else if (token.inversion === "6" || token.inversion === "6/5" || token.inversion === "/3") requiredPc = chord.pitchClasses[1];
  if (requiredPc == null) return [];
  if (v.B % 12 !== requiredPc) {
    return [{ type: "inversion", message: `Umkehrung gefordert: Bass muss die geforderte Stufe tragen (${token.inversion}).` }];
  }
  return [];
}

export function checkLeadingToneResolution(prev: SATBVoicing, next: SATBVoicing, ctx: KeyContext): CheckIssue[] {
  const issues: CheckIssue[] = [];
  // Compute tonic PC and leading tone PC
  const tonicPc = keyToTonicPc(ctx);
  const leadingPc = ((tonicPc + 11) % 12);
  ("S A T B".split(" ") as (keyof SATBVoicing)[]).forEach((part) => {
    const pPrev = prev[part] % 12;
    if (pPrev === leadingPc) {
      const isUp = next[part] > prev[part];
      const resolvesToTonic = (next[part] % 12) === tonicPc;
      if (!(isUp && resolvesToTonic)) {
        issues.push({ type: "leading_tone", message: `Leitton muss aufwärts zur Tonika gehen (${part}).`, parts: [part] });
      }
    }
  });
  return issues;
}

export function checkSeventhResolution(prevToken: FunctionToken | null, prev: SATBVoicing | null, next: SATBVoicing | null, ctx: KeyContext): CheckIssue[] {
  if (!prevToken || !prev || !next) return [];
  const chord = functionToChord(ctx, prevToken.func);
  if (!chord.isSeventh) return [];
  const seventhPc = chord.pitchClasses[3];
  const issues: CheckIssue[] = [];
  ("S A T B".split(" ") as (keyof SATBVoicing)[]).forEach((part) => {
    if (prev[part] % 12 === seventhPc) {
      const movesDown = next[part] < prev[part];
      if (!movesDown) {
        issues.push({ type: "seventh_resolution", message: `Septime muss abwärts gelöst werden (${part}).`, parts: [part] });
      }
    }
  });
  return issues;
}

function keyToTonicPc(ctx: KeyContext): number {
  const map: Record<string, number> = {
    C: 0, "B#": 0,
    "C#": 1, Db: 1,
    D: 2,
    "D#": 3, Eb: 3,
    E: 4, Fb: 4,
    F: 5, "E#": 5,
    "F#": 6, Gb: 6,
    G: 7,
    "G#": 8, Ab: 8,
    A: 9,
    "A#": 10, Bb: 10,
    B: 11, Cb: 11,
  };
  const k = ctx.key;
  if (!(k in map)) throw new Error(`Unknown key: ${k}`);
  return map[k];
}


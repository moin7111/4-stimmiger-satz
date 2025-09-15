import { ChordSpec, FunctionToken, SATBVoicing } from "./types";

// MIDI helpers
const NOTE_TO_MIDI_C4 = 60; // C4 midi

export const VOICE_RANGES = {
  S: { min: 60, max: 81 }, // C4..A5
  A: { min: 55, max: 74 }, // G3..D5
  T: { min: 48, max: 67 }, // C3..G4
  B: { min: 40, max: 60 }, // E2..C4
} as const;

// Build candidate absolute pitches (MIDI) for a pitch class within a range
function expandPitchClass(pc: number, minMidi: number, maxMidi: number): number[] {
  const results: number[] = [];
  for (let midi = minMidi; midi <= maxMidi; midi++) {
    if (midi % 12 === pc) results.push(midi);
  }
  return results;
}

function cartesian<T>(...arrays: T[][]): T[][] {
  return arrays.reduce<T[][]>((acc, arr) => {
    if (acc.length === 0) return arr.map((x) => [x]);
    const out: T[][] = [];
    for (const prev of acc) {
      for (const v of arr) out.push([...prev, v]);
    }
    return out;
  }, []);
}

function withinRanges(v: SATBVoicing): boolean {
  return (
    v.S >= VOICE_RANGES.S.min && v.S <= VOICE_RANGES.S.max &&
    v.A >= VOICE_RANGES.A.min && v.A <= VOICE_RANGES.A.max &&
    v.T >= VOICE_RANGES.T.min && v.T <= VOICE_RANGES.T.max &&
    v.B >= VOICE_RANGES.B.min && v.B <= VOICE_RANGES.B.max
  );
}

function spacingOk(v: SATBVoicing): boolean {
  // S-A <= octave, A-T <= octave, T-B <= 19 (duodecime)
  return (
    Math.abs(v.S - v.A) <= 12 &&
    Math.abs(v.A - v.T) <= 12 &&
    Math.abs(v.T - v.B) <= 19 &&
    v.S > v.A && v.A > v.T && v.T > v.B
  );
}

export function generateLegalVoicingsForChord(token: FunctionToken, chord: ChordSpec): SATBVoicing[] {
  const pcs = chord.pitchClasses;
  const toneCount = chord.isSeventh ? 4 : 3;
  const allowedDoublings = deriveAllowedDoublings(pcs, token, chord.isSeventh);

  const candidates: SATBVoicing[] = [];
  for (const doublingPc of allowedDoublings) {
    const toneSet = chord.isSeventh ? pcs : [...pcs, doublingPc];
    // Build pitch options per part
    const Sopts = expandPitchClassSet(toneSet as number[], VOICE_RANGES.S.min, VOICE_RANGES.S.max);
    const Aopts = expandPitchClassSet(toneSet as number[], VOICE_RANGES.A.min, VOICE_RANGES.A.max);
    const Topts = expandPitchClassSet(toneSet as number[], VOICE_RANGES.T.min, VOICE_RANGES.T.max);
    const Bopts = expandPitchClassSet(toneSet as number[], VOICE_RANGES.B.min, VOICE_RANGES.B.max);

    // Respect inversion for bass if specified
    const constrainedB = constrainBassByInversion(token, pcs, Bopts);

    for (const [S, A, T, B] of cartesian(Sopts, Aopts, Topts, constrainedB)) {
      const v: SATBVoicing = { S, A, T, B };
      if (!withinRanges(v)) continue;
      if (!spacingOk(v)) continue;
      if (!containsRequiredPcs(v, pcs)) continue;
      if (!doublingRespected(v, pcs, doublingPc, chord.isSeventh)) continue;
      candidates.push(v);
      if (candidates.length > 3000) break; // cap
    }
    if (candidates.length > 3000) break;
  }
  return dedupeVoicings(candidates);
}

function expandPitchClassSet(pcs: number[], min: number, max: number): number[] {
  const all: number[] = [];
  for (const pc of pcs) all.push(...expandPitchClass(pc, min, max));
  // unique
  return [...new Set(all)].sort((a, b) => a - b);
}

function dedupeVoicings(list: SATBVoicing[]): SATBVoicing[] {
  const seen = new Set<string>();
  const out: SATBVoicing[] = [];
  for (const v of list) {
    const key = `${v.S}-${v.A}-${v.T}-${v.B}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push(v);
    }
  }
  return out;
}

function containsRequiredPcs(v: SATBVoicing, pcs: number[]): boolean {
  const present = new Set([v.S % 12, v.A % 12, v.T % 12, v.B % 12]);
  return pcs.every((pc) => present.has(pc));
}

function countPcInVoicing(v: SATBVoicing, pc: number): number {
  return Number(v.S % 12 === pc) + Number(v.A % 12 === pc) + Number(v.T % 12 === pc) + Number(v.B % 12 === pc);
}

function doublingRespected(v: SATBVoicing, pcs: number[], doublingPc: number | null, isSeventh: boolean): boolean {
  if (isSeventh) {
    // do not double the seventh
    const seventhPc = pcs[3];
    return countPcInVoicing(v, seventhPc) <= 1;
  }
  if (doublingPc == null) return true;
  return countPcInVoicing(v, doublingPc) >= 2;
}

function deriveAllowedDoublings(pcs: number[], token: FunctionToken, isSeventh: boolean): (number | null)[] {
  if (isSeventh) return [null];
  // Heuristics per rules: prefer root; if first inversion, prefer bass or root; avoid doubling thirds in diminished
  const root = pcs[0];
  const third = pcs[1];
  const fifth = pcs[2];
  if (token.inversion === "6/4") {
    // Let the system be permissive
    return [root, fifth];
  }
  if (token.inversion === "6" || token.inversion === "6/5") {
    return [root, third];
  }
  return [root, fifth, third];
}

function constrainBassByInversion(token: FunctionToken, pcs: number[], bassOptions: number[]): number[] {
  if (!token.inversion) return bassOptions;
  let requiredPc: number | null = null;
  if (token.inversion === "6/4") requiredPc = pcs[2];
  else if (token.inversion === "6" || token.inversion === "6/5" || token.inversion === "/3") requiredPc = pcs[1];
  if (requiredPc == null) return bassOptions;
  return bassOptions.filter((m) => m % 12 === requiredPc);
}


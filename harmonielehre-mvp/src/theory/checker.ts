import { CheckIssue, SATBVoicing } from "./types";

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


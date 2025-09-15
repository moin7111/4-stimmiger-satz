import { FunctionToken, HarmonicFunctionSymbol, InversionFlag } from "./types";

const FUNC_RE = /^(T|S|D|TP|DD|D7|DD7)/i;

export function parseProgression(input: string): FunctionToken[] {
  const cleaned = input
    .replace(/\(/g, " ")
    .replace(/\)/g, " ")
    .replace(/,/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!cleaned) return [];

  const items = cleaned.split(/\s+/);
  const result: FunctionToken[] = [];

  for (const raw of items) {
    const m = raw.match(FUNC_RE);
    if (!m) continue;
    const func = m[1].toUpperCase() as HarmonicFunctionSymbol;
    const rest = raw.slice(m[0].length);
    const { inversion, suspension } = parseQualifiers(rest);
    result.push({ func, inversion, suspension, raw });
  }
  return result;
}

function parseQualifiers(rest: string): { inversion: InversionFlag; suspension: null | "6-5" | "4-3" } {
  let inversion: InversionFlag = null;
  let suspension: null | "6-5" | "4-3" = null;

  // Normalize separators
  const normalized = rest.replace(/[\s]+/g, "");

  // Check inversion patterns
  if (/\/3/.test(normalized) || /6\/?5?/.test(normalized)) {
    if (/6\/5/.test(normalized) || /aufder3/i.test(normalized) || /\/3/.test(normalized)) {
      inversion = "6/5";
    } else if (/6\/4/.test(normalized)) {
      inversion = "6/4";
    } else if (/6(?!\/\d)/.test(normalized)) {
      inversion = "6";
    }
  }

  // Check suspension
  if (/6-5/.test(normalized)) suspension = "6-5";
  if (/4-3/.test(normalized)) suspension = "4-3";

  return { inversion, suspension };
}


import { KeyContext, FunctionToken, CheckIssue, SATBVoicing } from "./types";
import { functionToChord } from "./key";
import { generateLegalVoicingsForChord } from "./voicing";
import { checkParallels, checkRangesAndCrossing, checkInversionRequirement, checkLeadingToneResolution, checkSeventhResolution } from "./checker";

export function evaluateUserVoicing(
  ctx: KeyContext,
  token: FunctionToken,
  prev: SATBVoicing | null,
  user: SATBVoicing
): { ok: boolean; issues: CheckIssue[]; allowedCount: number } {
  const chord = functionToChord(ctx, token.func);
  const allowed = generateLegalVoicingsForChord(token, chord);
  const contains = allowed.some((v) => v.S === user.S && v.A === user.A && v.T === user.T && v.B === user.B);
  const issues: CheckIssue[] = [];
  if (!contains) issues.push({ type: "not_in_allowed_voicings", message: "Voicing nicht in erlaubten Sätzen (Verdopplung/Umkehrung/Bereiche prüfen)." });
  issues.push(...checkRangesAndCrossing(user));
  issues.push(...checkInversionRequirement(token, ctx, user));
  if (prev) issues.push(...checkParallels(prev, user));
  if (prev) issues.push(...checkLeadingToneResolution(prev, user, ctx));
  if (prev) issues.push(...checkSeventhResolution(token, prev, user, ctx));
  return { ok: issues.length === 0, issues, allowedCount: allowed.length };
}


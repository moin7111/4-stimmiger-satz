export type Mode = "major" | "minor";

export type HarmonicFunctionSymbol =
  | "T"
  | "S"
  | "D"
  | "TP"
  | "DD"
  | "D7"
  | "DD7";

export type InversionFlag = null | "6" | "6/5" | "6/4" | "/3" | "/6" | "/5";

export interface FunctionToken {
  func: HarmonicFunctionSymbol;
  inversion: InversionFlag; // normalized: null | "6", "6/5", "6/4"
  suspension: null | "6-5" | "4-3";
  raw: string;
}

export type VoicePart = "S" | "A" | "T" | "B";

export interface KeyContext {
  key: string; // e.g., "C", "F#", "Eb"
  mode: Mode;
}

export interface ChordSpec {
  pitchClasses: number[]; // unique pitch classes (0..11), triad or seventh
  isSeventh: boolean;
}

export interface SATBVoicing {
  S: number; // midi
  A: number;
  T: number;
  B: number;
}

export interface CheckIssue {
  type:
    | "not_in_allowed_voicings"
    | "range"
    | "crossing"
    | "doubling"
    | "inversion"
    | "leading_tone"
    | "seventh_resolution"
    | "parallel"
    | "suspension";
  message: string;
  parts?: VoicePart[];
}


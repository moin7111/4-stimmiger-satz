const LETTER_TO_PC: Record<string, number> = {
  c: 0,
  d: 2,
  e: 4,
  f: 5,
  g: 7,
  a: 9,
  b: 11,
};

export function noteStringToPc(note: string): number {
  // accepts like "c/4", "c#/4", "db/4"
  const m = note.trim().toLowerCase().match(/^([a-g])([#b]?)/);
  if (!m) throw new Error(`Invalid note: ${note}`);
  const letter = m[1];
  const acc = m[2] || "";
  let pc = LETTER_TO_PC[letter];
  if (acc === "#") pc = (pc + 1) % 12;
  if (acc === "b") pc = (pc + 11) % 12;
  return pc;
}

export function noteStringToMidi(note: string): number {
  const m = note.trim().toLowerCase().match(/^([a-g])([#b]?)\/(\d+)$/);
  if (!m) throw new Error(`Invalid note: ${note}`);
  const pc = noteStringToPc(`${m[1]}${m[2]}`);
  const octave = parseInt(m[3], 10);
  return (octave + 1) * 12 + pc;
}

export function midiToNoteString(midi: number): string {
  const pc = ((midi % 12) + 12) % 12;
  const names = [
    "c",
    "c#",
    "d",
    "eb",
    "e",
    "f",
    "f#",
    "g",
    "ab",
    "a",
    "bb",
    "b",
  ];
  const octave = Math.floor(midi / 12) - 1;
  return `${names[pc]}/${octave}`;
}

export function satbNoteStringsToMidi(input: { S: string; A: string; T: string; B: string }): {
  S: number;
  A: number;
  T: number;
  B: number;
} {
  return {
    S: noteStringToMidi(input.S),
    A: noteStringToMidi(input.A),
    T: noteStringToMidi(input.T),
    B: noteStringToMidi(input.B),
  };
}


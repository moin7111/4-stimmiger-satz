import type { NextApiRequest, NextApiResponse } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).end("Method Not Allowed");
  }
  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const settings = await prisma.settings.findUnique({ where: { id: 1 } });
  if (settings?.selectionModel !== "RANKED") {
    return res.status(400).json({ error: "Allocation only for ranked model" });
  }

  const projects = await prisma.project.findMany();
  const students = await prisma.student.findMany({ include: { selections: true } });

  // Reset current assignments
  await prisma.student.updateMany({ data: { assignedProjectId: null } });

  // Randomized allocation: iterate 1st, then 2nd, then 3rd choices, shuffling students each round
  const capacityLeft = new Map<number, number>();
  projects.forEach((p) => capacityLeft.set(p.id, p.capacity));

  const assignedStudentIds = new Set<string>();

  const shuffleInPlace = <T,>(arr: T[]) => {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  };

  for (const priority of [1, 2, 3] as const) {
    const candidates = students.filter((s) => !assignedStudentIds.has(s.id) && s.selections.some((sel) => sel.rank === priority));
    shuffleInPlace(candidates);
    for (const student of candidates) {
      const choice = student.selections.find((s) => s.rank === priority);
      if (!choice) continue;
      const left = capacityLeft.get(choice.projectId) ?? 0;
      if (left > 0) {
        await prisma.student.update({ where: { id: student.id }, data: { assignedProjectId: choice.projectId } });
        capacityLeft.set(choice.projectId, left - 1);
        assignedStudentIds.add(student.id);
      }
    }
  }

  const result = await prisma.student.findMany({ include: { assignedProject: true, classGroup: true, selections: true } });

  // Compute summary statistics for ranks achieved
  let rank1 = 0, rank2 = 0, rank3 = 0, assigned = 0;
  for (const s of result) {
    if (s.assignedProjectId) {
      assigned++;
      const match = s.selections.find((sel) => sel.projectId === s.assignedProjectId);
      if (match?.rank === 1) rank1++;
      else if (match?.rank === 2) rank2++;
      else if (match?.rank === 3) rank3++;
    }
  }

  return res.status(200).json({
    students: result,
    summary: {
      total: result.length,
      assigned,
      unassigned: result.length - assigned,
      rank1,
      rank2,
      rank3,
    },
  });
}


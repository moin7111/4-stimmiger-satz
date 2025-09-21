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

  const projects = await prisma.project.findMany({ include: { selections: true } });
  const students = await prisma.student.findMany({ include: { selections: true } });

  // Reset current assignments
  await prisma.student.updateMany({ data: { assignedProjectId: null } });

  // Simple allocation: first try all rank 1, then 2, then 3 until full
  const capacityLeft = new Map<number, number>();
  projects.forEach((p) => capacityLeft.set(p.id, p.capacity));

  for (const priority of [1, 2, 3]) {
    for (const student of students) {
      if (student.assignedProjectId) continue;
      const choice = student.selections.find((s) => s.rank === priority);
      if (!choice) continue;
      const left = capacityLeft.get(choice.projectId) ?? 0;
      if (left > 0) {
        await prisma.student.update({ where: { id: student.id }, data: { assignedProjectId: choice.projectId } });
        capacityLeft.set(choice.projectId, left - 1);
      }
    }
  }

  const result = await prisma.student.findMany({ include: { assignedProject: true, classGroup: true } });
  return res.status(200).json(result);
}


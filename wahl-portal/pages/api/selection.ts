import type { NextApiRequest, NextApiResponse } from "next";
import { prisma } from "@/lib/prisma";
import { selectionDirectSchema, selectionRankedSchema } from "@/lib/validation";

async function handleDirect(studentId: string, projectId: number) {
  const project = await prisma.project.findUnique({
    where: { id: projectId },
    include: { studentsAssigned: true, allowedClasses: true },
  });
  if (!project) throw new Error("Project not found");
  if (project.studentsAssigned.length >= project.capacity) throw new Error("Project full");

  return prisma.student.update({
    where: { id: studentId },
    data: { assignedProjectId: projectId },
  });
}

async function handleRanked(studentId: string, choices: { projectId: number; rank: number }[]) {
  await prisma.studentSelection.deleteMany({ where: { studentId } });
  await prisma.student.update({ where: { id: studentId }, data: { assignedProjectId: null } });
  return prisma.studentSelection.createMany({
    data: choices.map((c) => ({ studentId, projectId: c.projectId, rank: c.rank })),
  });
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).end("Method Not Allowed");
  }

  const settings = await prisma.settings.findUnique({ where: { id: 1 } });
  const model = settings?.selectionModel || "DIRECT";

  if (model === "DIRECT") {
    const parsed = selectionDirectSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }
    try {
      // check eligibility
      const student = await prisma.student.findUnique({ where: { id: parsed.data.studentId } });
      if (!student) return res.status(404).json({ error: "Student not found" });
      const proj = await prisma.project.findUnique({ where: { id: parsed.data.projectId }, include: { allowedClasses: true } });
      if (!proj) return res.status(404).json({ error: "Project not found" });
      if (proj.allowedClasses.length > 0 && !proj.allowedClasses.some((ac) => ac.classGroupId === student.classGroupId)) {
        return res.status(400).json({ error: "Klasse nicht zugelassen" });
      }
      const result = await handleDirect(parsed.data.studentId, parsed.data.projectId);
      return res.status(200).json(result);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error";
      return res.status(400).json({ error: message });
    }
  } else {
    const parsed = selectionRankedSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }
    // eligibility check per choice
    const student = await prisma.student.findUnique({ where: { id: parsed.data.studentId } });
    if (!student) return res.status(404).json({ error: "Student not found" });
    const projects = await prisma.project.findMany({ where: { id: { in: parsed.data.choices.map((c) => c.projectId) } }, include: { allowedClasses: true } });
    for (const c of parsed.data.choices) {
      const proj = projects.find((p) => p.id === c.projectId);
      if (!proj) return res.status(404).json({ error: `Project ${c.projectId} not found` });
      if (proj.allowedClasses.length > 0 && !proj.allowedClasses.some((ac) => ac.classGroupId === student.classGroupId)) {
        return res.status(400).json({ error: `Klasse nicht zugelassen für Projekt ${proj.name}` });
      }
    }
    const result = await handleRanked(parsed.data.studentId, parsed.data.choices);
    return res.status(200).json(result);
  }
}


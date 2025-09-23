import type { NextApiRequest, NextApiResponse } from "next";
import type { Prisma } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import { studentCreateSchema, studentUpdateSchema } from "@/lib/validation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const { id, q, classGroupId, projectId, unassigned, take } = req.query as { id?: string; q?: string; classGroupId?: string; projectId?: string; unassigned?: string; take?: string };
    if (id) {
      const student = await prisma.student.findUnique({ where: { id }, include: { classGroup: true, selections: true, assignedProject: true } });
      if (!student) return res.status(404).json({ error: "Not found" });
      return res.status(200).json(student);
    }

    const where: Prisma.StudentWhereInput = {};
    if (q && q.trim()) {
      where.OR = [
        { firstName: { contains: q } },
        { lastName: { contains: q } },
      ];
    }
    if (classGroupId) {
      where.classGroupId = Number(classGroupId);
    }
    if (projectId) {
      // Match either assigned project or ranked choices include projectId
      where.OR = [
        ...(where.OR || []),
        { assignedProjectId: Number(projectId) },
        { selections: { some: { projectId: Number(projectId) } } },
      ];
    }

    if (unassigned === "true") {
      where.assignedProjectId = null;
    }

    const students = await prisma.student.findMany({
      where,
      include: { classGroup: true, selections: true, assignedProject: true },
      orderBy: [{ lastName: "asc" }, { firstName: "asc" }],
      take: take ? Number(take) : 100,
    });
    return res.status(200).json(students);
  }

  if (req.method === "POST") {
    const parsed = studentCreateSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }
    // Enforce single signup: prevent duplicate same person in same class
    const existing = await prisma.student.findFirst({
      where: {
        firstName: parsed.data.firstName,
        lastName: parsed.data.lastName,
        classGroupId: parsed.data.classGroupId,
      },
    });
    if (existing) {
      return res.status(409).json({ error: "Es existiert bereits eine Anmeldung mit diesen Daten." });
    }
    const created = await prisma.student.create({ data: parsed.data });
    return res.status(201).json(created);
  }

  if (req.method === "DELETE") {
    const session = await getServerSession(req, res, authOptions);
    if (!session) return res.status(401).json({ error: "Unauthorized" });
    const { id } = req.body as { id?: string };
    if (!id) return res.status(400).json({ error: "Missing id" });
    await prisma.studentSelection.deleteMany({ where: { studentId: id } });
    await prisma.student.delete({ where: { id } });
    return res.status(204).end();
  }

  if (req.method === "PUT") {
    const session = await getServerSession(req, res, authOptions);
    if (!session) return res.status(401).json({ error: "Unauthorized" });

    const parsed = studentUpdateSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }

    const { studentId, firstName, lastName, classGroupId, assignedProjectId, choices } = parsed.data;

    // Update basic fields and optional assignment
    const updated = await prisma.$transaction(async (tx) => {
      const updatedStudent = await tx.student.update({
        where: { id: studentId },
        data: {
          ...(firstName ? { firstName } : {}),
          ...(lastName ? { lastName } : {}),
          ...(classGroupId ? { classGroupId } : {}),
          ...(assignedProjectId !== undefined ? { assignedProjectId } : {}),
        },
      });

      if (choices) {
        // Switch to ranked choices: clear previous, set new, clear assignment
        await tx.studentSelection.deleteMany({ where: { studentId } });
        await tx.student.update({ where: { id: studentId }, data: { assignedProjectId: null } });
        await tx.studentSelection.createMany({ data: choices.map((c) => ({ studentId, projectId: c.projectId, rank: c.rank })) });
      }

      return updatedStudent;
    });

    return res.status(200).json(updated);
  }

  res.setHeader("Allow", ["GET", "POST", "PUT", "DELETE"]);
  return res.status(405).end("Method Not Allowed");
}


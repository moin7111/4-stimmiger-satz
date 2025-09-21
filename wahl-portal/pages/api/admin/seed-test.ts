import type { NextApiRequest, NextApiResponse } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

function randomInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).end("Method Not Allowed");
  }
  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const {
    students = 500,
    projects = 20,
    minCapacity = 15,
    maxCapacity = 30,
    classes = 5,
  } = (req.body || {}) as { students?: number; projects?: number; minCapacity?: number; maxCapacity?: number; classes?: number };

  try {
    await prisma.$transaction(async (tx) => {
      // Clean slate for core data (keep settings)
      await tx.studentSelection.deleteMany({});
      await tx.student.updateMany({ data: { assignedProjectId: null } });
      await tx.student.deleteMany({});
      await tx.projectAllowedClass.deleteMany({});
      await tx.project.deleteMany({});
      await tx.classGroup.deleteMany({});

      // Create class groups
      const classGroups = await Promise.all(
        Array.from({ length: classes }).map((_, i) => tx.classGroup.create({ data: { name: `Klasse ${i + 1}` } }))
      );

      // Create projects with varying capacities and allowed classes
      const createdProjects = [] as { id: number }[];
      for (let i = 0; i < projects; i++) {
        const capacity = randomInt(minCapacity, maxCapacity);
        const project = await tx.project.create({
          data: {
            name: `Projekt ${i + 1}`,
            leader: `Leitung ${i + 1}`,
            description: `Beschreibung für Projekt ${i + 1}`,
            capacity,
          },
        });
        createdProjects.push(project);
      }

      // Allow random subsets of classes per project (some all, some restricted)
      for (const p of createdProjects) {
        const allowed = classGroups.filter(() => Math.random() < 0.7); // ~70% of classes allowed
        const chosen = allowed.length > 0 ? allowed : classGroups.slice(0, 1);
        await tx.projectAllowedClass.createMany({ data: chosen.map((cg) => ({ projectId: p.id, classGroupId: cg.id })) });
      }

      // Create students
      const studentsCreated = [] as { id: string; classGroupId: number }[];
      for (let i = 0; i < students; i++) {
        const cg = classGroups[i % classGroups.length];
        const s = await tx.student.create({
          data: {
            firstName: `Vorname${i + 1}`,
            lastName: `Nachname${i + 1}`,
            classGroupId: cg.id,
          },
          select: { id: true, classGroupId: true },
        });
        studentsCreated.push(s);
      }

      // Create ranked choices for each student with weights favoring project 1st choice
      for (const s of studentsCreated) {
        // Choose only projects that allow the student's class
        const allowedProjectIds = (await tx.projectAllowedClass.findMany({ where: { classGroupId: s.classGroupId } })).map((x) => x.projectId);
        const available = createdProjects.filter((p) => allowedProjectIds.includes(p.id));

        // Pick 3 distinct projects at random
        const shuffled = available.slice();
        for (let i = shuffled.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        const picks = shuffled.slice(0, Math.min(3, shuffled.length));
        await tx.studentSelection.createMany({
          data: picks.map((p, idx) => ({ studentId: s.id, projectId: p.id, rank: idx + 1 })),
        });
      }
    });

    return res.status(200).json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return res.status(500).json({ error: message });
  }
}


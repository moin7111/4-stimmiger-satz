import type { NextApiRequest, NextApiResponse } from "next";
import { prisma } from "@/lib/prisma";
import { studentCreateSchema } from "@/lib/validation";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const { id } = req.query as { id?: string };
    if (id) {
      const student = await prisma.student.findUnique({ where: { id }, include: { classGroup: true } });
      if (!student) return res.status(404).json({ error: "Not found" });
      return res.status(200).json(student);
    }
    const students = await prisma.student.findMany({ include: { classGroup: true, selections: true } });
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

  res.setHeader("Allow", ["GET", "POST"]);
  return res.status(405).end("Method Not Allowed");
}


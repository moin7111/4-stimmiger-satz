import type { NextApiRequest, NextApiResponse } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { projectSchema } from "@/lib/validation";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const projects = await prisma.project.findMany({
      include: { allowedClasses: { include: { classGroup: true } } },
      orderBy: { name: "asc" },
    });
    return res.status(200).json(projects);
  }

  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  if (req.method === "POST") {
    const parsed = projectSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }
    const { name, leader, description, capacity, allowedClassIds } = parsed.data;
    const created = await prisma.project.create({
      data: {
        name,
        leader,
        description,
        capacity,
        allowedClasses: {
          create: allowedClassIds.map((classGroupId) => ({ classGroupId })),
        },
      },
      include: { allowedClasses: { include: { classGroup: true } } },
    });
    return res.status(201).json(created);
  }

  if (req.method === "PUT") {
    const { id } = req.body as { id?: number };
    if (!id) {
      return res.status(400).json({ error: "Missing id" });
    }
    const parsed = projectSchema.partial().safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }
    const { name, leader, description, capacity, allowedClassIds } = parsed.data;
    const updated = await prisma.project.update({
      where: { id },
      data: {
        ...(name ? { name } : {}),
        ...(leader ? { leader } : {}),
        ...(description !== undefined ? { description } : {}),
        ...(capacity ? { capacity } : {}),
        ...(allowedClassIds
          ? {
              allowedClasses: {
                deleteMany: {},
                create: allowedClassIds.map((classGroupId) => ({ classGroupId })),
              },
            }
          : {}),
      },
      include: { allowedClasses: { include: { classGroup: true } } },
    });
    return res.status(200).json(updated);
  }

  if (req.method === "DELETE") {
    const { id } = req.body as { id?: number };
    if (!id) {
      return res.status(400).json({ error: "Missing id" });
    }
    await prisma.project.delete({ where: { id } });
    return res.status(204).end();
  }

  res.setHeader("Allow", ["GET", "POST", "PUT", "DELETE"]);
  return res.status(405).end("Method Not Allowed");
}


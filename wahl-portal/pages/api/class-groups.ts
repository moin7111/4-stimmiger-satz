import type { NextApiRequest, NextApiResponse } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { classGroupSchema } from "@/lib/validation";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const classGroups = await prisma.classGroup.findMany({
      orderBy: { name: "asc" },
    });
    return res.status(200).json(classGroups);
  }

  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  if (req.method === "POST") {
    const parse = classGroupSchema.safeParse(req.body);
    if (!parse.success) {
      return res.status(400).json({ error: parse.error.flatten() });
    }
    const created = await prisma.classGroup.create({ data: parse.data });
    return res.status(201).json(created);
  }

  if (req.method === "PUT") {
    const { id, name } = req.body as { id?: number; name?: string };
    if (!id || !name) {
      return res.status(400).json({ error: "Missing id or name" });
    }
    const updated = await prisma.classGroup.update({ where: { id }, data: { name } });
    return res.status(200).json(updated);
  }

  if (req.method === "DELETE") {
    const { id } = req.body as { id?: number };
    if (!id) {
      return res.status(400).json({ error: "Missing id" });
    }
    await prisma.classGroup.delete({ where: { id } });
    return res.status(204).end();
  }

  res.setHeader("Allow", ["GET", "POST", "PUT", "DELETE"]);
  return res.status(405).end("Method Not Allowed");
}


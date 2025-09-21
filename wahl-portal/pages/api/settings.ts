import type { NextApiRequest, NextApiResponse } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === "GET") {
    const settings = await prisma.settings.upsert({
      where: { id: 1 },
      update: {},
      create: { id: 1 },
    });
    return res.status(200).json(settings);
  }

  if (req.method === "PUT") {
    const session = await getServerSession(req, res, authOptions);
    if (!session) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    const { selectionModel } = req.body as { selectionModel?: "DIRECT" | "RANKED" };
    if (!selectionModel || !["DIRECT", "RANKED"].includes(selectionModel)) {
      return res.status(400).json({ error: "Invalid selectionModel" });
    }
    const updated = await prisma.settings.update({
      where: { id: 1 },
      data: { selectionModel },
    });
    return res.status(200).json(updated);
  }

  res.setHeader("Allow", ["GET", "PUT"]);
  return res.status(405).end("Method Not Allowed");
}


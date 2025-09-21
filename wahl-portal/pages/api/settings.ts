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

  if (req.method === "DELETE") {
    const session = await getServerSession(req, res, authOptions);
    if (!session) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    const reset = await prisma.settings.upsert({
      where: { id: 1 },
      update: { selectionModel: "DIRECT" },
      create: { id: 1, selectionModel: "DIRECT" },
    });
    return res.status(200).json(reset);
  }

  if (req.method === "PUT") {
    const session = await getServerSession(req, res, authOptions);
    if (!session) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    const { selectionModel, selectionStartAt, selectionStartEnabled } = req.body as { selectionModel?: "DIRECT" | "RANKED"; selectionStartAt?: string | null; selectionStartEnabled?: boolean };

    if (!selectionModel && selectionStartAt === undefined && selectionStartEnabled === undefined) {
      return res.status(400).json({ error: "No updatable fields provided" });
    }

    const data: Record<string, unknown> = {};
    if (selectionModel) {
      if (!["DIRECT", "RANKED"].includes(selectionModel)) {
        return res.status(400).json({ error: "Invalid selectionModel" });
      }
      data.selectionModel = selectionModel;
    }
    if (selectionStartAt !== undefined) {
      if (selectionStartAt === null || selectionStartAt === "") {
        data.selectionStartAt = null;
      } else {
        const d = new Date(selectionStartAt);
        if (isNaN(d.getTime())) {
          return res.status(400).json({ error: "Invalid selectionStartAt" });
        }
        data.selectionStartAt = d;
      }
    }
    if (selectionStartEnabled !== undefined) {
      data.selectionStartEnabled = Boolean(selectionStartEnabled);
    }

    const updated = await prisma.settings.update({ where: { id: 1 }, data });
    return res.status(200).json(updated);
  }

  res.setHeader("Allow", ["GET", "DELETE", "PUT"]);
  return res.status(405).end("Method Not Allowed");
}


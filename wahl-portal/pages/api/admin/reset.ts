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

  try {
    await prisma.$transaction(async (tx) => {
      // Remove dependent data first
      await tx.studentSelection.deleteMany({});

      // Clear assignments and delete students before deleting related entities
      await tx.student.updateMany({ data: { assignedProjectId: null } });
      await tx.student.deleteMany({});

      // Remove project-class links, then projects
      await tx.projectAllowedClass.deleteMany({});
      await tx.project.deleteMany({});

      // Finally, remove classes
      await tx.classGroup.deleteMany({});

      // Reset settings to defaults
      await tx.settings.upsert({
        where: { id: 1 },
        update: { selectionModel: "DIRECT", selectionStartAt: null, selectionStartEnabled: false },
        create: { id: 1, selectionModel: "DIRECT", selectionStartEnabled: false },
      });
    });

    return res.status(200).json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return res.status(500).json({ error: message });
  }
}


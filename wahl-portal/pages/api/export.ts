import type { NextApiRequest, NextApiResponse } from "next";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { stringify } from "csv-stringify/sync";
import archiver from "archiver";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = await getServerSession(req, res, authOptions);
  if (!session) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const type = (req.query.type as string) || "overall";

  if (type === "overall") {
    const students = await prisma.student.findMany({
      include: { classGroup: true, assignedProject: true, selections: { include: { project: true } } },
      orderBy: [{ classGroup: { name: "asc" } }, { lastName: "asc" }, { firstName: "asc" }],
    });
    const rows = students.map((s) => ({
      firstName: s.firstName,
      lastName: s.lastName,
      class: s.classGroup.name,
      assignedProject: s.assignedProject?.name || "",
      choice1: s.selections.find((x) => x.rank === 1)?.project.name || "",
      choice2: s.selections.find((x) => x.rank === 2)?.project.name || "",
      choice3: s.selections.find((x) => x.rank === 3)?.project.name || "",
    }));
    const csv = "\uFEFF" + stringify(rows, { header: true, delimiter: ";" });
    res.setHeader("Content-Type", "text/csv; charset=utf-8");
    res.setHeader("Content-Disposition", "attachment; filename=overall.csv");
    return res.status(200).send(csv);
  }

  if (type === "by-project") {
    const students = await prisma.student.findMany({ include: { assignedProject: true, classGroup: true, selections: true } });
    const rows = students
      .filter((s) => s.assignedProject)
      .map((s) => ({
        project: s.assignedProject!.name,
        firstName: s.firstName,
        lastName: s.lastName,
        class: s.classGroup.name,
      }));
    const csv = "\uFEFF" + stringify(rows, { header: true, delimiter: ";" });
    res.setHeader("Content-Type", "text/csv; charset=utf-8");
    res.setHeader("Content-Disposition", "attachment; filename=by-project.csv");
    return res.status(200).send(csv);
  }

  if (type === "by-class-zip") {
    const classes = await prisma.classGroup.findMany({ include: { students: { include: { assignedProject: true, selections: { include: { project: true } } } } } });
    res.setHeader("Content-Type", "application/zip");
    res.setHeader("Content-Disposition", "attachment; filename=classes.zip");
    const archive = archiver("zip", { zlib: { level: 9 } });
    archive.pipe(res);
    for (const c of classes) {
      const rows = c.students.map((s) => ({
        firstName: s.firstName,
        lastName: s.lastName,
        class: c.name,
        assignedProject: s.assignedProject?.name || "",
        choice1: s.selections.find((x) => x.rank === 1)?.project.name || "",
        choice2: s.selections.find((x) => x.rank === 2)?.project.name || "",
        choice3: s.selections.find((x) => x.rank === 3)?.project.name || "",
      }));
      const csv = "\uFEFF" + stringify(rows, { header: true, delimiter: ";" });
      archive.append(csv, { name: `${c.name}.csv` });
    }
    await archive.finalize();
    return;
  }

  if (type === "by-project-zip") {
    const projects = await prisma.project.findMany({ include: { studentsAssigned: true } });
    const students = await prisma.student.findMany({ include: { classGroup: true } });
    res.setHeader("Content-Type", "application/zip");
    res.setHeader("Content-Disposition", "attachment; filename=projects.zip");
    const archive = archiver("zip", { zlib: { level: 9 } });
    archive.pipe(res);
    for (const p of projects) {
      const rows = students
        .filter((s) => s.assignedProjectId === p.id)
        .map((s) => ({
          firstName: s.firstName,
          lastName: s.lastName,
          class: s.classGroup.name,
        }));
      const csv = "\uFEFF" + stringify(rows, { header: true, delimiter: ";" });
      const safeName = p.name.replace(/[^a-zA-Z0-9-_]+/g, "_");
      archive.append(csv, { name: `${safeName}.csv` });
    }
    await archive.finalize();
    return;
  }

  return res.status(400).json({ error: "Unknown type" });
}


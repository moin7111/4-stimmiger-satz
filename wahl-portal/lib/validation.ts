import { z } from "zod";

export const classGroupSchema = z.object({
  name: z.string().min(1).max(50),
});

export const projectSchema = z.object({
  name: z.string().min(1).max(120),
  leader: z.string().min(1).max(120),
  description: z.string().max(2000).optional(),
  capacity: z.number().int().positive(),
  allowedClassIds: z.array(z.number().int().positive()).default([]),
});

export const studentCreateSchema = z.object({
  firstName: z.string().min(1).max(100),
  lastName: z.string().min(1).max(100),
  classGroupId: z.number().int().positive(),
});

export const studentUpdateSchema = z.object({
  studentId: z.string().uuid(),
  firstName: z.string().min(1).max(100).optional(),
  lastName: z.string().min(1).max(100).optional(),
  classGroupId: z.number().int().positive().optional(),
  assignedProjectId: z.number().int().positive().nullable().optional(),
  choices: z
    .array(
      z.object({
        projectId: z.number().int().positive(),
        rank: z.number().int().min(1).max(3),
      }),
    )
    .min(1)
    .max(3)
    .optional(),
});

export const selectionDirectSchema = z.object({
  studentId: z.string().uuid(),
  projectId: z.number().int().positive(),
});

export const selectionRankedSchema = z.object({
  studentId: z.string().uuid(),
  choices: z
    .array(
      z.object({
        projectId: z.number().int().positive(),
        rank: z.number().int().min(1).max(3),
      }),
    )
    .min(1)
    .max(3),
});


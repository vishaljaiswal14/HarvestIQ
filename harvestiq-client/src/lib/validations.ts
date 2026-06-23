import { z } from "zod";

export const phoneSchema = z
  .string()
  .min(10, "Phone number is too short")
  .regex(/^\+?[1-9]\d{1,14}$/, "Enter a valid phone number (E.164)");

export const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(50),
  phone: phoneSchema,
  password: z.string().min(8, "Password must be at least 8 characters"),
  preferred_lang: z.string().min(2).max(5),
});

export const loginSchema = z.object({
  phone: phoneSchema,
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const onboardingSchema = z.object({
  crop_type: z.string().min(1, "Crop type is required").max(50),
  state: z.string().min(1, "State is required").max(50),
  district: z.string().min(1, "District is required").max(50),
  sowing_date: z
    .string()
    .min(1, "Sowing date is required")
    .refine((value) => {
      const date = new Date(value);
      const today = new Date();
      today.setHours(23, 59, 59, 999);
      return !Number.isNaN(date.getTime()) && date <= today;
    }, "Sowing date cannot be in the future"),
  farm_name: z.string().max(100).optional(),
  soil_type: z.enum(["CLAY", "SANDY", "LOAM", "SILT"]).optional(),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;
export type LoginFormValues = z.infer<typeof loginSchema>;
export type OnboardingFormValues = z.infer<typeof onboardingSchema>;

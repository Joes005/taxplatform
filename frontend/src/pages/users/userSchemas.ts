import { z } from "zod";

const passwordRequirements =
  "At least 8 characters, with uppercase, lowercase, a digit, and a special character";

export const addUserSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  email: z.string().email("Enter a valid email address"),
  password: z
    .string()
    .min(8, passwordRequirements)
    .regex(/[A-Z]/, passwordRequirements)
    .regex(/[a-z]/, passwordRequirements)
    .regex(/\d/, passwordRequirements)
    .regex(/[^A-Za-z0-9]/, passwordRequirements),
  role_code: z.string().min(1, "Select a role"),
});
export type AddUserFormValues = z.infer<typeof addUserSchema>;

export const editUserSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  role_code: z.string().min(1, "Select a role"),
});
export type EditUserFormValues = z.infer<typeof editUserSchema>;

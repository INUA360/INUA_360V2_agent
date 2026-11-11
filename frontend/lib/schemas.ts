import { z } from "zod";

export const KENYA_COUNTIES = [
  "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
  "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
  "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos",
  "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a",
  "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu",
  "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
  "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
] as const;

export const SECTORS = [
  ["retail", "Retail / shop"],
  ["food_beverage", "Food & beverage"],
  ["agribusiness", "Agribusiness"],
  ["transport", "Transport / logistics"],
  ["services", "Services"],
  ["manufacturing", "Manufacturing"],
  ["construction", "Construction"],
  ["tech", "Tech / digital"],
  ["health", "Health"],
  ["education", "Education"],
  ["hospitality", "Hospitality"],
  ["other", "Other"],
] as const;

export const STRUCTURES = [
  ["sole_proprietor", "Sole proprietor"],
  ["partnership", "Partnership"],
  ["limited_company", "Limited company"],
  ["sacco_group", "SACCO / group"],
  ["other", "Other"],
] as const;

export const EMPLOYEE_BANDS = [
  ["0", "0"],
  ["1-5", "1–5"],
  ["6-20", "6–20"],
  ["21-50", "21–50"],
  ["50+", "50+"],
] as const;

export const businessSchema = z.object({
  name: z.string().min(2, "Enter your business name."),
  trading_name: z.string().optional().default(""),
  sector: z.string().min(1, "Choose a sector."),
  what_they_sell: z.string().min(3, "Describe what you sell."),
  county: z.string().min(1, "Choose a county."),
  town: z.string().min(1, "Enter your town."),
  started_on: z.string().min(1, "Enter the date you started."),
  structure: z.string().min(1, "Choose a structure."),
  employee_band: z.string().min(1, "Choose an employee band."),
  owner_name: z.string().min(2, "Enter the owner name."),
  owner_phone: z.string().min(7, "Enter the owner phone."),
});

export const complianceSchema = z.object({
  registration_status: z.enum(["registered", "not_registered", "unknown"]),
  registration_number: z.string().optional().default(""),
  kra_pin: z
    .string()
    .optional()
    .default("")
    .refine((value) => !value || /^[AP]\d{9}[A-Z]$/.test(value.toUpperCase()), {
      message: "Use a valid KRA PIN like P123456789A.",
    }),
  pin_status: z.enum(["active", "inactive", "unknown"]),
  tcc_status: z.enum(["valid", "expired", "none"]),
  tcc_expiry: z.string().optional().nullable(),
  county_permit_number: z.string().optional().default(""),
  county_permit_expiry: z.string().optional().nullable(),
  other_permits: z.array(z.object({ name: z.string(), expiry: z.string().nullable() })).optional().default([]),
});

export const fundingNeedSchema = z.object({
  amount: z.coerce.number().positive("Enter the amount you need."),
  purpose: z.enum(["working_capital", "stock", "equipment", "expansion", "other"]),
  description: z.string().optional().default(""),
  timeframe: z.enum(["immediate", "1_3_months", "3_6_months", "6_12_months", "flexible"]),
  avg_monthly_revenue: z.coerce.number().nonnegative().optional().nullable(),
  avg_monthly_expenses: z.coerce.number().nonnegative().optional().nullable(),
});

export const loanSchema = z.object({
  lender: z.string().min(2, "Enter the lender."),
  outstanding: z.coerce.number().nonnegative(),
  monthly_repayment: z.coerce.number().nonnegative(),
  ends_on: z.string().optional().nullable(),
});

export const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

export const registerSchema = z.object({
  email: z.email("Enter a valid email address."),
  phone: z.string().min(7, "Enter your phone number."),
  password: z.string().min(8, "Use at least 8 characters."),
  consent_given: z.literal(true, { message: "Consent is required." }),
});

export type BusinessFormValues = z.infer<typeof businessSchema>;
export type ComplianceFormValues = z.infer<typeof complianceSchema>;
export type FundingNeedFormValues = z.infer<typeof fundingNeedSchema>;
export type LoanFormValues = z.infer<typeof loanSchema>;

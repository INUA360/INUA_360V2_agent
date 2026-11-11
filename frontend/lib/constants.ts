export const DOCUMENT_TYPES = [
  ["business_registration_certificate", "Business registration certificate"],
  ["kra_pin_certificate", "KRA PIN certificate"],
  ["tcc", "Tax Compliance Certificate"],
  ["county_permit", "County business permit"],
  ["id_owner", "Owner ID"],
  ["business_plan", "Business plan"],
  ["bank_statement", "Bank statement"],
  ["lease_premises", "Lease / premises proof"],
  ["other", "Other"],
] as const;

export const LOAN_FIELDS = ["lender", "outstanding", "monthly_repayment", "ends_on"] as const;

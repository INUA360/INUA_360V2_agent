"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorBanner, SuccessBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { ApiError, api } from "@/lib/api";
import { errorMessage, firstFieldErrors } from "@/lib/format";
import { t } from "@/lib/i18n";
import { complianceSchema } from "@/lib/schemas";

const BLANK = {
  registration_status: "unknown",
  registration_number: "",
  kra_pin: "",
  pin_status: "unknown",
  tcc_status: "none",
  tcc_expiry: "",
  county_permit_number: "",
  county_permit_expiry: "",
};

export default function ComplianceStepPage() {
  const router = useRouter();
  const [values, setValues] = useState(BLANK);
  const [verification, setVerification] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .compliance()
      .then((compliance) => {
        setValues({
          registration_status: compliance.registration_status || "unknown",
          registration_number: compliance.registration_number || "",
          kra_pin: compliance.kra_pin || "",
          pin_status: compliance.pin_status || "unknown",
          tcc_status: compliance.tcc_status || "none",
          tcc_expiry: compliance.tcc_expiry || "",
          county_permit_number: compliance.county_permit_number || "",
          county_permit_expiry: compliance.county_permit_expiry || "",
        });
        setVerification(compliance.verification ?? {});
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 404) {
          router.replace("/onboarding/business");
        }
      });
  }, [router]);

  function update(key: keyof typeof BLANK, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const parsed = complianceSchema.safeParse({
      ...values,
      tcc_expiry: values.tcc_expiry || null,
      county_permit_expiry: values.county_permit_expiry || null,
    });
    if (!parsed.success) {
      setErrors(firstFieldErrors(parsed.error.flatten().fieldErrors));
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await api.saveCompliance({ ...parsed.data });
      setNotice(t("onboarding.compliance.saved"));
      router.push("/onboarding/financials");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-bold">{t("onboarding.step2.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("onboarding.step2.subtitle")}</p>
      <form className="card mt-5 space-y-4" onSubmit={submit} noValidate>
        {error ? <ErrorBanner message={error} /> : null}
        {notice ? <SuccessBanner message={notice} /> : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="registration_status" label={t("compliance.registrationStatus")} error={errors.registration_status}>
            <select id="registration_status" className="input" value={values.registration_status} onChange={(e) => update("registration_status", e.target.value)}>
              <option value="registered">{t("compliance.status.registered")}</option>
              <option value="not_registered">{t("compliance.status.not_registered")}</option>
              <option value="unknown">{t("compliance.status.unknown")}</option>
            </select>
          </Field>
          <Field id="registration_number" label={t("compliance.registrationNumber")} error={errors.registration_number}>
            <input id="registration_number" className="input" value={values.registration_number} onChange={(e) => update("registration_number", e.target.value)} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="kra_pin" label={t("compliance.kraPin")} error={errors.kra_pin} hint={t("compliance.selfReported")}>
            <input id="kra_pin" className="input uppercase" value={values.kra_pin} onChange={(e) => update("kra_pin", e.target.value)} maxLength={11} />
          </Field>
          <Field id="pin_status" label={t("compliance.pinStatus")} error={errors.pin_status}>
            <select id="pin_status" className="input" value={values.pin_status} onChange={(e) => update("pin_status", e.target.value)}>
              <option value="active">{t("compliance.status.active")}</option>
              <option value="inactive">{t("compliance.status.inactive")}</option>
              <option value="unknown">{t("compliance.status.unknown")}</option>
            </select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="tcc_status" label={t("compliance.tccStatus")} error={errors.tcc_status}>
            <select id="tcc_status" className="input" value={values.tcc_status} onChange={(e) => update("tcc_status", e.target.value)}>
              <option value="valid">{t("compliance.status.valid")}</option>
              <option value="expired">{t("compliance.status.expired")}</option>
              <option value="none">{t("compliance.status.none")}</option>
            </select>
          </Field>
          <Field id="tcc_expiry" label={t("compliance.tccExpiry")} error={errors.tcc_expiry}>
            <input id="tcc_expiry" type="date" className="input" value={values.tcc_expiry} onChange={(e) => update("tcc_expiry", e.target.value)} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="county_permit_number" label={t("compliance.permitNumber")} error={errors.county_permit_number}>
            <input id="county_permit_number" className="input" value={values.county_permit_number} onChange={(e) => update("county_permit_number", e.target.value)} />
          </Field>
          <Field id="county_permit_expiry" label={t("compliance.permitExpiry")} error={errors.county_permit_expiry}>
            <input id="county_permit_expiry" type="date" className="input" value={values.county_permit_expiry} onChange={(e) => update("county_permit_expiry", e.target.value)} />
          </Field>
        </div>
        <p className="text-xs text-slate-500">
          {t("compliance.selfReported")}: KRA PIN {verification.kra_pin ?? "—"} · TCC{" "}
          {verification.tcc ?? "—"}
        </p>
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? t("common.saving") : t("common.continue")}
        </button>
      </form>
    </section>
  );
}

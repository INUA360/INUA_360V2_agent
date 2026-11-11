"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorBanner, SuccessBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api } from "@/lib/api";
import { errorMessage, firstFieldErrors } from "@/lib/format";
import { t } from "@/lib/i18n";
import {
  EMPLOYEE_BANDS,
  KENYA_COUNTIES,
  SECTORS,
  STRUCTURES,
  businessSchema,
} from "@/lib/schemas";

const BLANK = {
  name: "",
  trading_name: "",
  sector: "",
  what_they_sell: "",
  county: "",
  town: "",
  started_on: "",
  structure: "",
  employee_band: "",
  owner_name: "",
  owner_phone: "",
};

export default function BusinessStepPage() {
  const router = useRouter();
  const [values, setValues] = useState(BLANK);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .business()
      .then((business) => {
        setValues({
          name: business.name ?? "",
          trading_name: business.trading_name ?? "",
          sector: business.sector ?? "",
          what_they_sell: business.what_they_sell ?? "",
          county: business.county ?? "",
          town: business.town ?? "",
          started_on: business.started_on ?? "",
          structure: business.structure ?? "",
          employee_band: business.employee_band ?? "",
          owner_name: business.owner_name ?? "",
          owner_phone: business.owner_phone ?? "",
        });
      })
      .catch(() => undefined);
  }, []);

  function update(key: keyof typeof BLANK, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const parsed = businessSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(firstFieldErrors(parsed.error.flatten().fieldErrors));
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await api.saveBusiness({ ...parsed.data });
      setNotice(t("onboarding.business.saved"));
      router.push("/onboarding/compliance");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-bold">{t("onboarding.step1.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("onboarding.step1.subtitle")}</p>
      <form className="card mt-5 space-y-4" onSubmit={submit} noValidate>
        {error ? <ErrorBanner message={error} /> : null}
        {notice ? <SuccessBanner message={notice} /> : null}
        <Field id="name" label={t("business.name")} error={errors.name}>
          <input id="name" className="input" value={values.name} onChange={(e) => update("name", e.target.value)} required />
        </Field>
        <Field id="trading_name" label={`${t("business.tradingName")} (${t("common.optional")})`} error={errors.trading_name}>
          <input id="trading_name" className="input" value={values.trading_name} onChange={(e) => update("trading_name", e.target.value)} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="sector" label={t("business.sector")} error={errors.sector}>
            <select id="sector" className="input" value={values.sector} onChange={(e) => update("sector", e.target.value)} required>
              <option value="">—</option>
              {SECTORS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Field>
          <Field id="county" label={t("business.county")} error={errors.county}>
            <select id="county" className="input" value={values.county} onChange={(e) => update("county", e.target.value)} required>
              <option value="">—</option>
              {KENYA_COUNTIES.map((county) => (
                <option key={county} value={county}>{county}</option>
              ))}
            </select>
          </Field>
        </div>
        <Field id="what_they_sell" label={t("business.sells")} error={errors.what_they_sell}>
          <textarea id="what_they_sell" className="input min-h-24" value={values.what_they_sell} onChange={(e) => update("what_they_sell", e.target.value)} maxLength={500} required />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="town" label={t("business.town")} error={errors.town}>
            <input id="town" className="input" value={values.town} onChange={(e) => update("town", e.target.value)} required />
          </Field>
          <Field id="started_on" label={t("business.startedOn")} error={errors.started_on}>
            <input id="started_on" type="date" className="input" value={values.started_on} onChange={(e) => update("started_on", e.target.value)} required />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="structure" label={t("business.structure")} error={errors.structure}>
            <select id="structure" className="input" value={values.structure} onChange={(e) => update("structure", e.target.value)} required>
              <option value="">—</option>
              {STRUCTURES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Field>
          <Field id="employee_band" label={t("business.employees")} error={errors.employee_band}>
            <select id="employee_band" className="input" value={values.employee_band} onChange={(e) => update("employee_band", e.target.value)} required>
              <option value="">—</option>
              {EMPLOYEE_BANDS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="owner_name" label={t("business.ownerName")} error={errors.owner_name}>
            <input id="owner_name" className="input" value={values.owner_name} onChange={(e) => update("owner_name", e.target.value)} required />
          </Field>
          <Field id="owner_phone" label={t("business.ownerPhone")} error={errors.owner_phone}>
            <input id="owner_phone" type="tel" className="input" value={values.owner_phone} onChange={(e) => update("owner_phone", e.target.value)} required />
          </Field>
        </div>
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? t("common.saving") : t("common.continue")}
        </button>
      </form>
    </section>
  );
}

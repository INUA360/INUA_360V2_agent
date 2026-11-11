"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, Loading, SuccessBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api } from "@/lib/api";
import { errorMessage, firstFieldErrors } from "@/lib/format";
import { t } from "@/lib/i18n";
import { fundingNeedSchema } from "@/lib/schemas";

const PURPOSES = ["working_capital", "stock", "equipment", "expansion", "other"] as const;
const TIMEFRAMES = ["immediate", "1_3_months", "3_6_months", "6_12_months", "flexible"] as const;

export function FundingNeedForm({ onSaved }: { onSaved?: () => void }) {
  const [loaded, setLoaded] = useState(false);
  const [amount, setAmount] = useState("");
  const [purpose, setPurpose] = useState<string>("working_capital");
  const [timeframe, setTimeframe] = useState<string>("flexible");
  const [description, setDescription] = useState("");
  const [revenue, setRevenue] = useState("");
  const [expenses, setExpenses] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .fundingNeed()
      .then((data) => {
        if (!active) return;
        setAmount(String(data.amount ?? ""));
        setPurpose(String(data.purpose ?? "working_capital"));
        setTimeframe(String(data.timeframe ?? "flexible"));
        setDescription(String(data.description ?? ""));
        setRevenue(String(data.avg_monthly_revenue ?? ""));
        setExpenses(String(data.avg_monthly_expenses ?? ""));
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    const parsed = fundingNeedSchema.safeParse({
      amount,
      purpose,
      description,
      timeframe,
      avg_monthly_revenue: revenue === "" ? undefined : revenue,
      avg_monthly_expenses: expenses === "" ? undefined : expenses,
    });
    if (!parsed.success) {
      setErrors(firstFieldErrors(parsed.error.flatten().fieldErrors));
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await api.saveFundingNeed({ ...parsed.data });
      setNotice(t("financials.needSaved"));
      onSaved?.();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return <Loading />;

  return (
    <form className="card space-y-4" onSubmit={submit} noValidate aria-labelledby="funding-need">
      <h2 id="funding-need" className="text-base font-semibold">
        {t("financials.fundingNeed")}
      </h2>
      {error ? <ErrorBanner message={error} /> : null}
      {notice ? <SuccessBanner message={notice} /> : null}
      <Field id="need_amount" label={t("financials.need.amount")} error={errors.amount}>
        <input
          id="need_amount"
          type="number"
          min="1"
          step="1"
          className="input"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="need_purpose" label={t("financials.need.purpose")}>
          <select
            id="need_purpose"
            className="input"
            value={purpose}
            onChange={(event) => setPurpose(event.target.value)}
          >
            {PURPOSES.map((value) => (
              <option key={value} value={value}>
                {t(`financials.purpose.${value}`)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="need_timeframe" label={t("financials.needTimeframeLabel")}>
          <select
            id="need_timeframe"
            className="input"
            value={timeframe}
            onChange={(event) => setTimeframe(event.target.value)}
          >
            {TIMEFRAMES.map((value) => (
              <option key={value} value={value}>
                {t(`financials.timeframe.${value}`)}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field id="need_description" label={t("financials.need.description")}>
        <textarea
          id="need_description"
          className="input min-h-24"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={500}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="need_revenue" label={t("financials.selfReportedRevenue")} error={errors.avg_monthly_revenue}>
          <input
            id="need_revenue"
            type="number"
            min="0"
            step="1"
            className="input"
            value={revenue}
            onChange={(event) => setRevenue(event.target.value)}
          />
        </Field>
        <Field id="need_expenses" label={t("financials.selfReportedExpenses")} error={errors.avg_monthly_expenses}>
          <input
            id="need_expenses"
            type="number"
            min="0"
            step="1"
            className="input"
            value={expenses}
            onChange={(event) => setExpenses(event.target.value)}
          />
        </Field>
      </div>
      <button type="submit" className="btn-primary" disabled={busy}>
        {busy ? t("common.saving") : t("common.save")}
      </button>
    </form>
  );
}

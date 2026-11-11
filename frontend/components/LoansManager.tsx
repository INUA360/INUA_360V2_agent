"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorBanner, Loading } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api, type LoanRow } from "@/lib/api";
import { errorMessage, firstFieldErrors, formatDate, formatKes } from "@/lib/format";
import { t } from "@/lib/i18n";
import { loanSchema } from "@/lib/schemas";

function rowsFrom(payload: { results?: LoanRow[] } | LoanRow[]): LoanRow[] {
  return Array.isArray(payload) ? payload : (payload.results ?? []);
}

export function LoansManager({ onChanged }: { onChanged?: () => void }) {
  const [rows, setRows] = useState<LoanRow[] | null>(null);
  const [lender, setLender] = useState("");
  const [outstanding, setOutstanding] = useState("");
  const [repayment, setRepayment] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setRows(rowsFrom(await api.loans()));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const parsed = loanSchema.safeParse({
      lender,
      outstanding,
      monthly_repayment: repayment,
      ends_on: endsOn || null,
    });
    if (!parsed.success) {
      setErrors(firstFieldErrors(parsed.error.flatten().fieldErrors));
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await api.createLoan({ ...parsed.data });
      setLender("");
      setOutstanding("");
      setRepayment("");
      setEndsOn("");
      await load();
      onChanged?.();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    try {
      await api.deleteLoan(id);
      await load();
      onChanged?.();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!rows && !error) return <Loading />;

  return (
    <section className="card space-y-4" aria-labelledby="loans-heading">
      <h2 id="loans-heading" className="text-base font-semibold">
        {t("financials.loans")}
      </h2>
      {error ? <ErrorBanner message={error} onRetry={load} /> : null}
      {rows?.length ? (
        <ul className="divide-y divide-slate-100">
          {rows.map((loan) => (
            <li key={loan.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <p className="text-sm font-medium text-slate-800">{loan.lender}</p>
                <p className="text-xs text-slate-500">
                  {formatKes(loan.outstanding)} · {formatKes(loan.monthly_repayment)}/mo ·{" "}
                  {formatDate(loan.ends_on)}
                </p>
              </div>
              <button
                type="button"
                className="btn-danger"
                onClick={() => remove(loan.id)}
                disabled={busy}
              >
                {t("common.delete")}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">{t("financials.noLoans")}</p>
      )}

      <form className="space-y-4 border-t border-slate-100 pt-4" onSubmit={submit} noValidate>
        <h3 className="text-sm font-semibold">{t("financials.addLoan")}</h3>
        <Field id="loan_lender" label={t("financials.loan.lender")} error={errors.lender}>
          <input
            id="loan_lender"
            className="input"
            value={lender}
            onChange={(event) => setLender(event.target.value)}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="loan_outstanding" label={t("financials.loan.outstanding")} error={errors.outstanding}>
            <input
              id="loan_outstanding"
              type="number"
              min="0"
              step="1"
              className="input"
              value={outstanding}
              onChange={(event) => setOutstanding(event.target.value)}
            />
          </Field>
          <Field id="loan_repayment" label={t("financials.loan.repayment")} error={errors.monthly_repayment}>
            <input
              id="loan_repayment"
              type="number"
              min="0"
              step="1"
              className="input"
              value={repayment}
              onChange={(event) => setRepayment(event.target.value)}
            />
          </Field>
        </div>
        <Field id="loan_ends" label={t("financials.loan.endsOn")} error={errors.ends_on}>
          <input
            id="loan_ends"
            type="date"
            className="input"
            value={endsOn}
            onChange={(event) => setEndsOn(event.target.value)}
          />
        </Field>
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? t("common.saving") : t("common.add")}
        </button>
      </form>
    </section>
  );
}

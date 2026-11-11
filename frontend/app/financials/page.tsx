"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ErrorBanner, Loading } from "@/components/Feedback";
import { FundingNeedForm } from "@/components/FundingNeedForm";
import { LoansManager } from "@/components/LoansManager";
import { StatementUpload } from "@/components/StatementUpload";
import { ApiError, api } from "@/lib/api";
import { errorMessage, formatKes, formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

type Summary = {
  has_statement: boolean;
  months_of_data: number;
  average_monthly_inflow: string;
  average_monthly_outflow: string;
  revenue_consistency_cv: number | null;
  net_cash_flow_positive_ratio: number | null;
  debt_service_ratio: number | null;
  revenue_caveat: string | null;
};

type MonthRow = {
  month: string;
  inflow: string;
  outflow: string;
  net: string;
  txn_count: number;
};

export default function FinancialsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [months, setMonths] = useState<MonthRow[]>([]);
  const [noBusiness, setNoBusiness] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, monthlyData] = await Promise.all([
        api.financialSummary(),
        api.monthly(),
      ]);
      setSummary(summaryData as unknown as Summary);
      setMonths(monthlyData as unknown as MonthRow[]);
      setNoBusiness(false);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) setNoBusiness(true);
      else setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("nav.financials")}</h1>
      {loading ? <Loading /> : null}
      {error ? <ErrorBanner message={error} onRetry={load} /> : null}
      {noBusiness ? (
        <div className="card mt-4">
          <p className="text-sm text-slate-700">{t("dashboard.noBusiness")}</p>
          <Link href="/onboarding/business" className="btn-primary mt-3 no-underline">
            {t("dashboard.setupBusiness")}
          </Link>
        </div>
      ) : null}

      {summary ? (
        <section className="card mt-4" aria-labelledby="fin-summary">
          <h2 id="fin-summary" className="text-base font-semibold">
            {t("dashboard.snapshot")}
          </h2>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-slate-500">{t("dashboard.avgInflow")}</dt>
              <dd className="font-medium">{formatKes(summary.average_monthly_inflow)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("dashboard.avgOutflow")}</dt>
              <dd className="font-medium">{formatKes(summary.average_monthly_outflow)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("dashboard.months")}</dt>
              <dd className="font-medium">{formatNumber(summary.months_of_data)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("dashboard.dataConfidence")}</dt>
              <dd className="font-medium">{summary.has_statement ? "—" : t("common.none")}</dd>
            </div>
          </dl>
          {summary.revenue_caveat ? (
            <p className="mt-3 text-xs text-slate-500">{summary.revenue_caveat}</p>
          ) : null}
        </section>
      ) : null}

      <div className="mt-5 space-y-5">
        <StatementUpload onConfirmed={load} />
        <FundingNeedForm onSaved={load} />
        <LoansManager onChanged={load} />
      </div>

      <section className="card mt-5" aria-labelledby="monthly-heading">
        <h2 id="monthly-heading" className="text-base font-semibold">
          {t("financials.summary")}
        </h2>
        {months.length ? (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-3">{t("financials.month")}</th>
                  <th className="py-2 pr-3 text-right">{t("financials.inflow")}</th>
                  <th className="py-2 pr-3 text-right">{t("financials.outflow")}</th>
                  <th className="py-2 pr-3 text-right">{t("financials.net")}</th>
                  <th className="py-2 text-right">{t("financials.transactions")}</th>
                </tr>
              </thead>
              <tbody>
                {months.map((row) => (
                  <tr key={row.month} className="border-b border-slate-100">
                    <td className="py-2 pr-3">{row.month.slice(0, 7)}</td>
                    <td className="py-2 pr-3 text-right">{formatKes(row.inflow)}</td>
                    <td className="py-2 pr-3 text-right">{formatKes(row.outflow)}</td>
                    <td className="py-2 pr-3 text-right">{formatKes(row.net)}</td>
                    <td className="py-2 text-right">{row.txn_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">{t("financials.noMonthly")}</p>
        )}
      </section>
    </AppShell>
  );
}

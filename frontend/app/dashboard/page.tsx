"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ErrorBanner, Loading } from "@/components/Feedback";
import { OpportunityCard } from "@/components/OpportunityCard";
import { ScoreDisplay } from "@/components/ScoreDisplay";
import {
  ApiError,
  api,
  type Business,
  type OpportunityMatch,
  type ReadinessResponse,
} from "@/lib/api";
import { errorMessage, formatKes, formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

type Summary = {
  has_statement: boolean;
  months_of_data: number;
  average_monthly_inflow: string;
  average_monthly_outflow: string;
  revenue_consistency_cv: number | null;
  data_confidence: string;
};

export default function DashboardPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [matches, setMatches] = useState<OpportunityMatch[]>([]);
  const [noBusiness, setNoBusiness] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const current = await api.business();
      setBusiness(current);
      setNoBusiness(false);
      const [readinessData, summaryData, matchData] = await Promise.all([
        api.readiness(),
        api.financialSummary(),
        api.matches(),
      ]);
      setReadiness(readinessData);
      setSummary(summaryData as unknown as Summary);
      setMatches(matchData);
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
      <h1 className="text-2xl font-bold">{t("dashboard.title")}</h1>
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

      {readiness ? (
        <div className="mt-4">
          <ScoreDisplay assessment={readiness.latest} disclaimer={readiness.disclaimer} />
        </div>
      ) : null}

      {summary ? (
        <section className="card mt-5" aria-labelledby="snapshot-heading">
          <h2 id="snapshot-heading" className="text-base font-semibold">
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
              <dt className="text-slate-500">{t("dashboard.consistency")}</dt>
              <dd className="font-medium">
                {summary.revenue_consistency_cv === null
                  ? "—"
                  : summary.revenue_consistency_cv.toFixed(2)}
              </dd>
            </div>
          </dl>
          {!summary.has_statement ? (
            <Link href="/financials" className="btn-secondary mt-4 no-underline">
              {t("financials.uploadTitle")}
            </Link>
          ) : null}
        </section>
      ) : null}

      {business ? (
        <section className="mt-6" aria-labelledby="matches-heading">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 id="matches-heading" className="text-lg font-semibold">
              {t("dashboard.topMatches")}
            </h2>
            <Link href="/opportunities" className="text-sm font-semibold text-brand-700">
              {t("dashboard.viewAll")}
            </Link>
          </div>
          {matches.length ? (
            <div className="grid gap-3">
              {matches.slice(0, 3).map((match) => (
                <OpportunityCard key={match.id} match={match} />
              ))}
            </div>
          ) : (
            <p className="card text-sm text-slate-600">{t("dashboard.noMatches")}</p>
          )}
        </section>
      ) : null}
    </AppShell>
  );
}

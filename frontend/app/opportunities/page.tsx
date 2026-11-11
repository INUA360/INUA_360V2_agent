"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ErrorBanner, Loading } from "@/components/Feedback";
import { OpportunityCard } from "@/components/OpportunityCard";
import { ApiError, api, type OpportunityMatch } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import { t } from "@/lib/i18n";

const FILTERS = ["all", "strong", "possible", "stretch"] as const;

export default function OpportunitiesPage() {
  const [matches, setMatches] = useState<OpportunityMatch[] | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [noBusiness, setNoBusiness] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setMatches(await api.matches());
      setNoBusiness(false);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) setNoBusiness(true);
      else setError(errorMessage(caught));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function setState(match: OpportunityMatch, state: string) {
    setBusyId(match.id);
    try {
      await api.updateMatchState(match.id, state);
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusyId(null);
    }
  }

  const visible =
    filter === "all" ? matches ?? [] : (matches ?? []).filter((match) => match.fit_level === filter);

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("opportunities.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("opportunities.subtitle")}</p>

      {error ? <ErrorBanner message={error} onRetry={load} /> : null}
      {noBusiness ? (
        <div className="card mt-4">
          <p className="text-sm text-slate-700">{t("dashboard.noBusiness")}</p>
          <Link href="/onboarding/business" className="btn-primary mt-3 no-underline">
            {t("dashboard.setupBusiness")}
          </Link>
        </div>
      ) : null}

      {!matches && !error && !noBusiness ? <Loading /> : null}

      {matches ? (
        <>
          <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label={t("opportunities.filter")}>
            {FILTERS.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
                className={filter === value ? "btn-primary" : "btn-secondary"}
              >
                {value === "all" ? t("opportunities.all") : t(`opportunities.fit.${value}`)}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-4">
            {visible.length ? (
              visible.map((match) => (
                <div key={match.id}>
                  <OpportunityCard match={match} />
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="text-xs text-slate-500">
                      {t("opportunities.yourFit")}: {t(`opportunities.state.${match.state}`)}
                    </span>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busyId === match.id || match.state === "saved"}
                      onClick={() => setState(match, "saved")}
                    >
                      {t("opportunities.save")}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={busyId === match.id || match.state === "applied"}
                      onClick={() => setState(match, "applied")}
                    >
                      {t("opportunities.applied")}
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      disabled={busyId === match.id}
                      onClick={() => setState(match, "dismissed")}
                    >
                      {t("opportunities.dismiss")}
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p className="card text-sm text-slate-600">{t("opportunities.noMatches")}</p>
            )}
          </div>
        </>
      ) : null}
    </AppShell>
  );
}

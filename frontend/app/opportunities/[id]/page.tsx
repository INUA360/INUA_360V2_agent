"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ChecklistView } from "@/components/ChecklistView";
import { ErrorBanner, Loading } from "@/components/Feedback";
import { FitBadge } from "@/components/OpportunityCard";
import { api, type Checklist, type OpportunityMatch } from "@/lib/api";
import { errorMessage, formatDate, formatKes } from "@/lib/format";
import { t } from "@/lib/i18n";

export default function OpportunityDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [match, setMatch] = useState<OpportunityMatch | null>(null);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [checklistData, matches] = await Promise.all([api.checklist(id), api.matches()]);
      setChecklist(checklistData);
      setMatch(matches.find((item) => item.opportunity.id === id) ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setState(state: string) {
    if (!match) return;
    setBusy(true);
    try {
      await api.updateMatchState(match.id, state);
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <Link href="/opportunities" className="text-sm font-semibold text-brand-700">
        ← {t("opportunities.backToList")}
      </Link>
      {loading ? <Loading /> : null}
      {error ? <ErrorBanner message={error} onRetry={load} /> : null}

      {checklist ? (
        <div className="mt-4 space-y-4">
          <section className="card">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h1 className="text-2xl font-bold">{checklist.opportunity.name}</h1>
                <p className="text-sm text-slate-500">{checklist.opportunity.provider}</p>
              </div>
              {match ? <FitBadge fit={match.fit_level} /> : null}
            </div>
            <p className="mt-3 text-sm text-slate-700">{checklist.opportunity.description}</p>
            {checklist.opportunity.application_url ? (
              <a
                href={checklist.opportunity.application_url}
                target="_blank"
                rel="noreferrer noopener"
                className="btn-primary mt-4 no-underline"
              >
                {t("opportunities.openApplication")}
              </a>
            ) : null}
          </section>

          {match ? (
            <section className="card" aria-labelledby="explanation-heading">
              <h2 id="explanation-heading" className="text-base font-semibold">
                {t("opportunities.yourFit")}
              </h2>
              <p className="mt-2 text-sm text-slate-700">{match.explanation.summary}</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <h3 className="text-sm font-medium text-brand-700">{t("opportunities.met")}</h3>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                    {match.explanation.met.map((item) => (
                      <li key={item.key}>{item.label}: {item.detail}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-amber-700">{t("opportunities.missing")}</h3>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                    {match.explanation.missing.map((item) => (
                      <li key={item.key}>{item.label}: {item.detail}</li>
                    ))}
                  </ul>
                </div>
              </div>
              {match.explanation.moves_to_strong.length ? (
                <div className="mt-3">
                  <h3 className="text-sm font-medium text-slate-700">
                    {t("opportunities.movesToStrong")}
                  </h3>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                    {match.explanation.moves_to_strong.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-slate-500">{t("opportunities.amount")}</dt>
                  <dd>{formatKes(match.opportunity.min_amount)} – {formatKes(match.opportunity.max_amount)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t("opportunities.deadline")}</dt>
                  <dd>{formatDate(match.opportunity.deadline)}</dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => setState("saved")}>
                  {t("opportunities.save")}
                </button>
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => setState("applied")}>
                  {t("opportunities.applied")}
                </button>
                <button type="button" className="btn-danger" disabled={busy} onClick={() => setState("dismissed")}>
                  {t("opportunities.dismiss")}
                </button>
              </div>
            </section>
          ) : null}

          <ChecklistView checklist={checklist} />
        </div>
      ) : null}
    </AppShell>
  );
}

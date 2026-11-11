"use client";

import type { ReadinessAssessment } from "@/lib/api";
import { t } from "@/lib/i18n";

export function ScoreDisplay({
  assessment,
  disclaimer,
}: {
  assessment: ReadinessAssessment;
  disclaimer?: string;
}) {
  const confidence = assessment.data_confidence;
  return (
    <section aria-labelledby="score-heading" className="space-y-4">
      <div className="card">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="score-heading" className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              {t("dashboard.score")}
            </h2>
            <p className="mt-1 text-5xl font-bold text-brand-700">
              {assessment.total_score}
              <span className="ml-1 text-xl text-slate-400">/100</span>
            </p>
          </div>
          <div className="text-right">
            <span className="pill bg-brand-50 capitalize text-brand-700">{assessment.band}</span>
            <p className="mt-2 text-xs text-slate-500">
              {t("dashboard.dataConfidence")}:{" "}
              {t(`dashboard.dataConfidence.${confidence}`)}
            </p>
          </div>
        </div>
        <div
          className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"
          role="img"
          aria-label={`${assessment.total_score} out of 100`}
        >
          <div
            className="h-full rounded-full bg-brand-600"
            style={{ width: `${Math.min(Math.max(assessment.total_score, 0), 100)}%` }}
          />
        </div>
        <p className="mt-3 text-xs text-slate-500">{t("dashboard.notCreditScore")}</p>
        {confidence === "low" ? (
          <p className="mt-2 text-xs font-medium text-amber-700">
            {t("dashboard.lowConfidence")}
          </p>
        ) : null}
        {disclaimer ? <p className="mt-3 text-xs text-slate-500">{disclaimer}</p> : null}
      </div>

      <div className="card">
        <h3 className="text-base font-semibold">{t("dashboard.components")}</h3>
        <ul className="mt-3 space-y-3">
          {assessment.component_scores.map((component) => {
            const percent =
              component.max_points > 0
                ? Math.round((component.points / component.max_points) * 100)
                : 0;
            return (
              <li key={component.key}>
                <div className="flex items-baseline justify-between gap-2 text-sm">
                  <span className="font-medium text-slate-800">{component.label}</span>
                  <span className="shrink-0 text-slate-500">
                    {component.points}/{component.max_points}
                  </span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand-500" style={{ width: `${percent}%` }} />
                </div>
                <p className="mt-1 text-xs text-slate-500">{component.explanation}</p>
              </li>
            );
          })}
        </ul>
      </div>

      {assessment.gaps.length > 0 ? (
        <div className="card">
          <h3 className="text-base font-semibold">{t("dashboard.improve")}</h3>
          <ul className="mt-3 space-y-3">
            {assessment.gaps.map((gap) => (
              <li key={gap.key} className="rounded-xl border border-slate-200 p-3">
                <p className="text-sm font-medium text-slate-800">{gap.message}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {gap.action} · +{gap.points_gain} {t("dashboard.pointsGain")}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

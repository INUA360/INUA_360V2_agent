"use client";

import Link from "next/link";

import type { OpportunityMatch } from "@/lib/api";
import { formatDate, formatKes } from "@/lib/format";
import { t } from "@/lib/i18n";

const FIT_STYLES: Record<string, string> = {
  strong: "bg-brand-50 text-brand-700",
  possible: "bg-amber-50 text-amber-800",
  stretch: "bg-slate-100 text-slate-700",
};

export function FitBadge({ fit }: { fit: string }) {
  return (
    <span className={`pill ${FIT_STYLES[fit] ?? FIT_STYLES.stretch}`}>
      {t(`opportunities.fit.${fit}`)}
    </span>
  );
}

export function OpportunityCard({ match }: { match: OpportunityMatch }) {
  const opportunity = match.opportunity;
  return (
    <article className="card">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{opportunity.name}</h2>
          <p className="text-sm text-slate-500">{opportunity.provider}</p>
        </div>
        <FitBadge fit={match.fit_level} />
      </div>
      <p className="mt-2 text-sm text-slate-600">{match.explanation.summary}</p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
        <div>
          <dt className="font-medium text-slate-500">{t("opportunities.amount")}</dt>
          <dd>
            {formatKes(opportunity.min_amount)} – {formatKes(opportunity.max_amount)}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">{t("opportunities.deadline")}</dt>
          <dd>{formatDate(opportunity.deadline)}</dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href={`/opportunities/${opportunity.id}`} className="btn-secondary no-underline">
          {t("common.view")}
        </Link>
        {opportunity.application_url ? (
          <a
            href={opportunity.application_url}
            target="_blank"
            rel="noreferrer noopener"
            className="btn-secondary no-underline"
          >
            {t("opportunities.openApplication")}
          </a>
        ) : null}
      </div>
    </article>
  );
}

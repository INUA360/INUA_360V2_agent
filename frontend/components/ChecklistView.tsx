"use client";

import Link from "next/link";

import type { Checklist } from "@/lib/api";
import { t } from "@/lib/i18n";

export function ChecklistView({ checklist }: { checklist: Checklist }) {
  return (
    <section aria-labelledby="checklist-heading" className="card">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="checklist-heading" className="text-base font-semibold">
          {t("opportunities.checklist")}
        </h2>
        <p className="text-sm text-slate-600">{checklist.summary}</p>
      </div>
      <ul className="mt-4 space-y-2">
        {checklist.items.map((item) => {
          const done = item.status === "done";
          return (
            <li key={item.key} className="flex items-start gap-3 rounded-xl border border-slate-200 p-3">
              <span
                aria-hidden="true"
                className={`mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  done ? "bg-brand-50 text-brand-700" : "bg-amber-50 text-amber-700"
                }`}
              >
                {done ? "✓" : "!"}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800">
                  {item.label}{" "}
                  <span className="sr-only">
                    {done ? t("documents.present") : t("documents.missing")}
                  </span>
                </p>
                <p className="text-xs text-slate-500">{item.detail}</p>
                {!done ? (
                  <Link href={item.fix_path} className="mt-1 inline-block text-xs font-semibold text-brand-700">
                    {t("dashboard.nextStep")}
                  </Link>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

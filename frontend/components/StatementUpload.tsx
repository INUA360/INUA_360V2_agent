"use client";

import { useState } from "react";

import { ErrorBanner, SuccessBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api, type StatementPreview } from "@/lib/api";
import { errorMessage, formatDate, formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export function StatementUpload({ onConfirmed }: { onConfirmed?: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [preview, setPreview] = useState<StatementPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function parse(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    setPreview(null);
    try {
      const result = await api.parseStatement(file, password);
      setPreview(result);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  async function confirm() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      await api.confirmStatement(preview.pending_id);
      setPreview(null);
      setFile(null);
      setNotice(`${t("financials.confirmed")} ${t("financials.caveat")}`);
      onConfirmed?.();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="statement-upload" className="card space-y-4">
      <div>
        <h2 id="statement-upload" className="text-base font-semibold">
          {t("financials.uploadTitle")}
        </h2>
        <p className="mt-1 text-sm text-slate-600">{t("financials.uploadHelp")}</p>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {notice ? <SuccessBanner message={notice} /> : null}

      <form className="space-y-4" onSubmit={parse}>
        <Field id="statement_file" label={t("financials.file")}>
          <input
            id="statement_file"
            type="file"
            accept="application/pdf"
            className="input py-2"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
        </Field>
        <Field id="statement_password" label={t("financials.password")} hint={t("privacy.statement")}>
          <input
            id="statement_password"
            type="password"
            autoComplete="off"
            className="input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <button type="submit" className="btn-primary" disabled={busy || !file}>
          {busy ? t("financials.parsing") : t("financials.parse")}
        </button>
      </form>

      {preview ? (
        <div className="rounded-xl border border-brand-100 bg-brand-50 p-4">
          <h3 className="text-base font-semibold text-brand-700">{t("financials.previewTitle")}</h3>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">{t("financials.period")}</dt>
              <dd>
                {formatDate(preview.summary.period_start)} – {formatDate(preview.summary.period_end)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("financials.rows")}</dt>
              <dd>{formatNumber(preview.summary.rows_parsed)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("financials.skipped")}</dt>
              <dd>{formatNumber(preview.summary.rows_skipped)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("dashboard.dataConfidence")}</dt>
              <dd>{preview.summary.confidence}</dd>
            </div>
          </dl>

          {preview.summary.warnings.length ? (
            <div className="mt-3">
              <p className="text-sm font-medium text-amber-800">{t("financials.warnings")}</p>
              <ul className="mt-1 list-inside list-disc text-xs text-amber-800">
                {preview.summary.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {preview.summary.preview.length ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-brand-100 text-slate-600">
                    <th className="py-1 pr-2">{t("common.date")}</th>
                    <th className="py-1 pr-2">{t("common.details")}</th>
                    <th className="py-1 text-right">{t("common.amount")}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.summary.preview.slice(0, 5).map((row) => (
                    <tr key={`${row.source_ref}-${row.occurred_at}`} className="border-b border-brand-100/60">
                      <td className="py-1 pr-2">{formatDate(row.occurred_at)}</td>
                      <td className="max-w-48 truncate py-1 pr-2">{row.counterparty_text || row.category}</td>
                      <td className="py-1 text-right">{row.direction === "in" ? "+" : "-"}{row.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-3 text-sm text-amber-800">{t("financials.noRows")}</p>
          )}

          <button
            type="button"
            className="btn-primary mt-4"
            onClick={confirm}
            disabled={busy}
          >
            {busy ? t("common.loading") : t("financials.confirm")}
          </button>
          <p className="mt-2 text-xs text-slate-600">{t("financials.caveat")}</p>
        </div>
      ) : null}
    </section>
  );
}

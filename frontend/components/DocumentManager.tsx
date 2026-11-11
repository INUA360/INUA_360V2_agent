"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorBanner, Loading, SuccessBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api, type DocumentsResponse } from "@/lib/api";
import { DOCUMENT_TYPES } from "@/lib/constants";
import { errorMessage, formatDate } from "@/lib/format";
import { t } from "@/lib/i18n";

export function DocumentManager() {
  const [data, setData] = useState<DocumentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [docType, setDocType] = useState<string>(DOCUMENT_TYPES[0][0]);
  const [file, setFile] = useState<File | null>(null);
  const [expiry, setExpiry] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api.documents());
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.uploadDocument(file, docType, expiry || undefined);
      setNotice(t("documents.uploaded"));
      setFile(null);
      setExpiry("");
      const form = event.currentTarget;
      form.reset();
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm(t("documents.deleteConfirm"))) return;
    setBusy(true);
    try {
      await api.deleteDocument(id);
      setNotice(t("common.deleted"));
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (!data && !error) return <Loading />;

  const documents = data?.documents ?? data?.results ?? [];

  return (
    <div className="space-y-5">
      {error ? <ErrorBanner message={error} onRetry={load} /> : null}
      {notice ? <SuccessBanner message={notice} /> : null}

      <section className="card" aria-labelledby="doc-checklist">
        <h2 id="doc-checklist" className="text-base font-semibold">
          {t("documents.checklist")}
        </h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {(data?.checklist ?? []).map((item) => (
            <li key={item.doc_type} className="flex items-center justify-between gap-2 text-sm">
              <span>{item.label}</span>
              <span className={`pill ${item.present ? "bg-brand-50 text-brand-700" : "bg-slate-100 text-slate-600"}`}>
                {item.present ? t("documents.present") : t("documents.missing")}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <form className="card space-y-4" onSubmit={upload}>
        <h2 className="text-base font-semibold">{t("common.upload")}</h2>
        <Field id="doc_type" label={t("documents.type")}>
          <select
            id="doc_type"
            className="input"
            value={docType}
            onChange={(event) => setDocType(event.target.value)}
          >
            {DOCUMENT_TYPES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="doc_file" label={t("documents.file")}>
          <input
            id="doc_file"
            type="file"
            accept="application/pdf,image/jpeg,image/png"
            className="input py-2"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
        </Field>
        <Field id="doc_expiry" label={t("documents.expiry")}>
          <input
            id="doc_expiry"
            type="date"
            className="input"
            value={expiry}
            onChange={(event) => setExpiry(event.target.value)}
          />
        </Field>
        <button type="submit" className="btn-primary" disabled={busy || !file}>
          {busy ? t("common.loading") : t("common.upload")}
        </button>
      </form>

      <section className="card" aria-labelledby="doc-list">
        <h2 id="doc-list" className="text-base font-semibold">
          {t("documents.uploaded")}
        </h2>
        {documents.length ? (
          <ul className="mt-3 divide-y divide-slate-100">
            {documents.map((document) => (
              <li key={document.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{document.doc_type_label}</p>
                  <p className="text-xs text-slate-500">
                    {document.filename} · {formatDate(document.created_at)}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => remove(document.id)}
                  disabled={busy}
                  aria-label={`${t("common.delete")} ${document.doc_type_label}`}
                >
                  {t("common.delete")}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-500">{t("documents.noDocuments")}</p>
        )}
      </section>
    </div>
  );
}

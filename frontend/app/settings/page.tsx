"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ErrorBanner, Loading, SuccessBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { ApiError, api, type Business, type User } from "@/lib/api";
import { errorMessage, formatDate } from "@/lib/format";
import { t } from "@/lib/i18n";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [business, setBusiness] = useState<Business | null>(null);
  const [phone, setPhone] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.me(), api.business().catch(() => null)])
      .then(([me, biz]) => {
        setUser(me);
        setPhone(me.phone);
        setBusiness(biz);
      })
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  async function savePhone(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.updateMe({ phone });
      setUser(updated);
      setNotice(t("common.saved"));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function deleteData() {
    if (confirmText !== "DELETE") {
      setError(t("settings.deleteMismatch"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.deleteMyData();
      api.clearToken();
      router.replace("/");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        api.clearToken();
        router.replace("/login");
      } else {
        setError(errorMessage(caught));
      }
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <AppShell>
        {error ? <ErrorBanner message={error} /> : <Loading />}
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
      {error ? <ErrorBanner message={error} /> : null}
      {notice ? <SuccessBanner message={notice} /> : null}

      <section className="card mt-4" aria-labelledby="account-heading">
        <h2 id="account-heading" className="text-base font-semibold">
          {t("settings.account")}
        </h2>
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-slate-500">{t("settings.email")}</dt>
            <dd className="font-medium">{user.email}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-slate-500">{t("settings.consent")}</dt>
            <dd className="font-medium">
              {user.consent_at ? `${t("settings.consentGiven")} · ${formatDate(user.consent_at)}` : "—"}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-slate-500">{t("settings.onboarding")}</dt>
            <dd className="font-medium">{user.onboarding_percent}%</dd>
          </div>
          {business ? (
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">{t("settings.business")}</dt>
              <dd className="font-medium">{business.name}</dd>
            </div>
          ) : null}
        </dl>
        <form className="mt-4 max-w-sm space-y-3" onSubmit={savePhone}>
          <Field id="phone" label={t("settings.phone")}>
            <input
              id="phone"
              type="tel"
              className="input"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
            />
          </Field>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? t("common.saving") : t("common.save")}
          </button>
        </form>
      </section>

      <section className="card mt-5 border-red-200" aria-labelledby="delete-heading">
        <h2 id="delete-heading" className="text-base font-semibold text-red-800">
          {t("settings.deleteData")}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{t("settings.deleteWarning")}</p>
        <div className="mt-4 max-w-sm space-y-3">
          <Field id="delete_confirm" label={t("settings.deleteType")}>
            <input
              id="delete_confirm"
              className="input"
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              autoComplete="off"
            />
          </Field>
          <button type="button" className="btn-danger" disabled={busy} onClick={deleteData}>
            {t("settings.deleteConfirm")}
          </button>
        </div>
      </section>
    </AppShell>
  );
}

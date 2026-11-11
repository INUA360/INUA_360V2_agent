"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ErrorBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import { t } from "@/lib/i18n";
import { registerSchema } from "@/lib/schemas";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const parsed = registerSchema.safeParse({
      email,
      phone,
      password,
      consent_given: consent,
    });
    if (!parsed.success) {
      const flat = parsed.error.flatten().fieldErrors;
      setErrors({
        email: flat.email?.[0] ?? "",
        phone: flat.phone?.[0] ?? "",
        password: flat.password?.[0] ?? "",
        consent_given: flat.consent_given?.[0] ?? "",
      });
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await api.register({
        email: parsed.data.email,
        phone: parsed.data.phone,
        password: parsed.data.password,
        consent_version: t("auth.register.consentVersion"),
        consent_given: parsed.data.consent_given,
      });
      router.replace("/onboarding/business");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="mx-auto w-full max-w-md px-4 py-10">
      <Link href="/" className="text-lg font-bold text-brand-700">
        {t("app.name")}
      </Link>
      <h1 className="mt-8 text-2xl font-bold">{t("auth.register.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("auth.register.subtitle")}</p>

      <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
        {error ? <ErrorBanner message={error} /> : null}
        <Field id="email" label={t("auth.login.email")} error={errors.email}>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="input"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(errors.email)}
            required
          />
        </Field>
        <Field id="phone" label={t("auth.register.phone")} error={errors.phone}>
          <input
            id="phone"
            type="tel"
            autoComplete="tel"
            className="input"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            aria-invalid={Boolean(errors.phone)}
            required
          />
        </Field>
        <Field id="password" label={t("auth.login.password")} error={errors.password}>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            className="input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={Boolean(errors.password)}
            required
          />
        </Field>
        <div>
          <label className="flex items-start gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 rounded border-slate-300"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
              aria-invalid={Boolean(errors.consent_given)}
              required
            />
            <span>{t("auth.register.consent")}</span>
          </label>
          {errors.consent_given ? (
            <p role="alert" className="error-text">
              {errors.consent_given}
            </p>
          ) : null}
          <p className="mt-1 text-xs text-slate-500">{t("auth.register.consentVersion")}</p>
        </div>
        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {busy ? t("common.loading") : t("auth.register.submit")}
        </button>
      </form>

      <p className="mt-6 text-sm text-slate-600">
        {t("auth.register.hasAccount")}{" "}
        <Link href="/login" className="font-semibold text-brand-700">
          {t("auth.login.submit")}
        </Link>
      </p>
    </main>
  );
}

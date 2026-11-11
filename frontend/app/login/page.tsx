"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ErrorBanner } from "@/components/Feedback";
import { Field } from "@/components/Field";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/format";
import { t } from "@/lib/i18n";
import { loginSchema } from "@/lib/schemas";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      const flat = parsed.error.flatten().fieldErrors;
      setErrors({
        email: flat.email?.[0] ?? "",
        password: flat.password?.[0] ?? "",
      });
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      await api.login(parsed.data.email, parsed.data.password);
      router.replace("/dashboard");
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
      <h1 className="mt-8 text-2xl font-bold">{t("auth.login.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("auth.login.subtitle")}</p>

      <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
        {error ? <ErrorBanner message={error} /> : null}
        <Field id="email" label={t("auth.login.email")} error={errors.email}>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            className="input"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            required
          />
        </Field>
        <Field id="password" label={t("auth.login.password")} error={errors.password}>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            className="input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
            required
          />
        </Field>
        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {busy ? t("common.loading") : t("auth.login.submit")}
        </button>
      </form>

      <p className="mt-6 text-sm text-slate-600">
        {t("auth.login.noAccount")}{" "}
        <Link href="/signup" className="font-semibold text-brand-700">
          {t("auth.register.submit")}
        </Link>
      </p>
    </main>
  );
}

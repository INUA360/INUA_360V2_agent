import Link from "next/link";

import { t } from "@/lib/i18n";

export default function LandingPage() {
  return (
    <main id="main" className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-4 py-10">
      <header className="mb-10">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">
          {t("app.name")}
        </p>
        <h1 className="mt-2 text-3xl font-bold leading-tight text-slate-900 sm:text-4xl">
          {t("app.tagline")}
        </h1>
        <p className="mt-4 text-base text-slate-600">{t("landing.hero")}</p>
        <p className="mt-3 text-sm text-slate-500">{t("app.positioning")}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/signup" className="btn-primary no-underline">
            {t("landing.start")}
          </Link>
          <Link href="/login" className="btn-secondary no-underline">
            {t("landing.login")}
          </Link>
        </div>
      </header>

      <section aria-labelledby="honest" className="grid gap-4 sm:grid-cols-3">
        <h2 id="honest" className="sr-only">
          {t("privacy.title")}
        </h2>
        {[t("landing.honest1"), t("landing.honest2"), t("landing.honest3")].map((copy) => (
          <div key={copy} className="card text-sm text-slate-700">
            {copy}
          </div>
        ))}
      </section>

      <footer className="mt-auto pt-10 text-xs text-slate-500">
        <p>{t("privacy.statement")}</p>
      </footer>
    </main>
  );
}

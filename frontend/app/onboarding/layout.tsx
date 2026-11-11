"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AuthGuard } from "@/components/AuthGuard";
import { t } from "@/lib/i18n";

const STEPS = [
  { href: "/onboarding/business", key: "onboarding.step1" },
  { href: "/onboarding/compliance", key: "onboarding.step2" },
  { href: "/onboarding/financials", key: "onboarding.step3" },
  { href: "/onboarding/documents", key: "onboarding.step4" },
];

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const currentIndex = Math.max(
    STEPS.findIndex((step) => pathname.startsWith(step.href)),
    0,
  );

  return (
    <AuthGuard>
      <div className="min-h-dvh">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
            <Link href="/dashboard" className="text-lg font-bold text-brand-700 no-underline">
              {t("app.name")}
            </Link>
            <Link href="/dashboard" className="text-sm font-medium text-slate-600">
              {t("onboarding.continueLater")}
            </Link>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-3xl px-4 py-6">
          <nav aria-label={t("onboarding.progress")} className="mb-6">
            <p className="mb-2 text-sm font-medium text-slate-600">
              {t("common.step")} {currentIndex + 1} {t("common.of")} {STEPS.length}
            </p>
            <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {STEPS.map((step, index) => {
                const active = index === currentIndex;
                const done = index < currentIndex;
                return (
                  <li key={step.href}>
                    <Link
                      href={step.href}
                      aria-current={active ? "step" : undefined}
                      className={`flex min-h-12 items-center rounded-xl border px-3 py-2 text-sm font-medium no-underline ${
                        active
                          ? "border-brand-600 bg-brand-50 text-brand-700"
                          : done
                            ? "border-brand-100 bg-white text-brand-700"
                            : "border-slate-200 bg-white text-slate-600"
                      }`}
                    >
                      <span className="mr-2 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs">
                        {done ? "✓" : index + 1}
                      </span>
                      {t(step.key)}
                    </Link>
                  </li>
                );
              })}
            </ol>
          </nav>
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}

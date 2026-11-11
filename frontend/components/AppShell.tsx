"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Loading } from "@/components/Feedback";
import { api, type User } from "@/lib/api";
import { t } from "@/lib/i18n";

const NAV = [
  { href: "/dashboard", key: "nav.dashboard" },
  { href: "/financials", key: "nav.financials" },
  { href: "/documents", key: "nav.documents" },
  { href: "/opportunities", key: "nav.opportunities" },
  { href: "/settings", key: "nav.settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  const load = useCallback(async () => {
    if (!api.hasToken()) {
      router.replace("/login");
      return;
    }
    try {
      setUser(await api.me());
    } catch {
      api.clearToken();
      router.replace("/login");
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function logout() {
    await api.logout();
    router.replace("/login");
  }

  if (!user) return <Loading />;

  return (
    <div className="min-h-dvh pb-24 md:pb-0">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link href="/dashboard" className="text-lg font-bold text-brand-700 no-underline">
            {t("app.name")}
          </Link>
          <nav aria-label={t("nav.main")} className="hidden items-center gap-1 md:flex">
            {NAV.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-lg px-3 py-2 text-sm font-medium no-underline ${
                    active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {t(item.key)}
                </Link>
              );
            })}
            <button type="button" className="btn-secondary ml-2" onClick={logout}>
              {t("nav.logout")}
            </button>
          </nav>
          <div className="text-right text-xs text-slate-500 md:hidden">
            <p className="max-w-40 truncate">{user.email}</p>
            <button type="button" className="font-semibold text-brand-700" onClick={logout}>
              {t("nav.logout")}
            </button>
          </div>
        </div>
        {user.onboarding_percent < 100 ? (
          <div className="bg-brand-50">
            <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm text-brand-700">
              <span>
                {t("onboarding.progress")}: {user.onboarding_percent}%
              </span>
              <Link href="/onboarding/business" className="font-semibold text-brand-700">
                {t("dashboard.nextStep")}
              </Link>
            </div>
          </div>
        ) : null}
      </header>

      <main id="main" className="mx-auto w-full max-w-5xl px-4 py-6">
        {children}
      </main>

      <nav
        aria-label={t("nav.main")}
        className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t border-slate-200 bg-white py-1 md:hidden"
      >
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-12 min-w-14 flex-col items-center justify-center rounded-lg px-2 text-xs font-medium no-underline ${
                active ? "text-brand-700" : "text-slate-500"
              }`}
            >
              {t(item.key)}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

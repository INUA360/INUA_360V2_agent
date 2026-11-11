"use client";

import { useRouter } from "next/navigation";

import { DocumentManager } from "@/components/DocumentManager";
import { t } from "@/lib/i18n";

export default function DocumentsStepPage() {
  const router = useRouter();

  return (
    <section>
      <h1 className="text-2xl font-bold">{t("onboarding.step4.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("onboarding.step4.subtitle")}</p>
      <div className="mt-5 space-y-5">
        <DocumentManager />
        <div className="flex justify-between gap-3">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => router.push("/onboarding/financials")}
          >
            {t("common.back")}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => router.push("/dashboard")}
          >
            {t("common.finish")}
          </button>
        </div>
      </div>
    </section>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { FundingNeedForm } from "@/components/FundingNeedForm";
import { StatementUpload } from "@/components/StatementUpload";
import { ApiError, api } from "@/lib/api";
import { t } from "@/lib/i18n";

export default function FinancialsStepPage() {
  const router = useRouter();

  useEffect(() => {
    api.business().catch((caught) => {
      if (caught instanceof ApiError && caught.status === 404) {
        router.replace("/onboarding/business");
      }
    });
  }, [router]);

  return (
    <section>
      <h1 className="text-2xl font-bold">{t("onboarding.step3.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("onboarding.step3.subtitle")}</p>
      <div className="mt-5 space-y-5">
        <StatementUpload />
        <FundingNeedForm />
        <div className="flex justify-between gap-3">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => router.push("/onboarding/compliance")}
          >
            {t("common.back")}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => router.push("/onboarding/documents")}
          >
            {t("common.continue")}
          </button>
        </div>
      </div>
    </section>
  );
}

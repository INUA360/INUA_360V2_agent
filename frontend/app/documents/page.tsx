"use client";

import { AppShell } from "@/components/AppShell";
import { DocumentManager } from "@/components/DocumentManager";
import { t } from "@/lib/i18n";

export default function DocumentsPage() {
  return (
    <AppShell>
      <h1 className="text-2xl font-bold">{t("documents.title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("documents.subtitle")}</p>
      <div className="mt-4">
        <DocumentManager />
      </div>
    </AppShell>
  );
}

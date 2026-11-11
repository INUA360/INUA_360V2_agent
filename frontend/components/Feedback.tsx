"use client";

import { t } from "@/lib/i18n";

export function Loading({ label }: { label?: string }) {
  return (
    <p role="status" className="py-6 text-sm text-slate-600">
      {label ?? t("common.loading")}
    </p>
  );
}

export function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
    >
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="btn-secondary mt-3" onClick={onRetry}>
          {t("common.retry")}
        </button>
      ) : null}
    </div>
  );
}

export function SuccessBanner({ message }: { message: string }) {
  return (
    <div
      role="status"
      className="mb-4 rounded-xl border border-brand-100 bg-brand-50 p-4 text-sm text-brand-700"
    >
      {message}
    </div>
  );
}

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChecklistView } from "@/components/ChecklistView";
import type { Checklist } from "@/lib/api";

const checklist: Checklist = {
  opportunity: {
    id: "op-1",
    name: "Example working capital loan",
    provider: "EXAMPLE — provider",
    application_url: "https://example.com",
    description: "Working capital for small shops.",
  },
  items: [
    {
      key: "compliance:pin",
      label: "KRA PIN",
      status: "done",
      detail: "Provided.",
      fix_path: "/onboarding/compliance",
    },
    {
      key: "document:tcc",
      label: "Tax Compliance Certificate",
      status: "missing",
      detail: "Upload this document.",
      fix_path: "/documents",
    },
  ],
  requirements_met: 1,
  requirements_total: 2,
  summary: "1 of 2 requirements met",
};

describe("ChecklistView", () => {
  it("renders each requirement and links missing items to a fix path", () => {
    render(<ChecklistView checklist={checklist} />);

    expect(screen.getByText("1 of 2 requirements met")).toBeInTheDocument();
    expect(screen.getByText("KRA PIN")).toBeInTheDocument();
    expect(screen.getByText("Upload this document.")).toBeInTheDocument();
    const fixLink = screen.getByRole("link", { name: "Next step" });
    expect(fixLink).toHaveAttribute("href", "/documents");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreDisplay } from "@/components/ScoreDisplay";
import type { ReadinessAssessment } from "@/lib/api";

const assessment: ReadinessAssessment = {
  id: "1",
  total_score: 62,
  band: "Developing",
  component_scores: [
    {
      key: "trading_history",
      label: "Trading history",
      points: 18,
      max_points: 25,
      explanation: "Two years of records.",
    },
    {
      key: "cash_flow",
      label: "Cash flow",
      points: 14,
      max_points: 25,
      explanation: "Some volatility.",
    },
  ],
  gaps: [
    {
      key: "document:tcc",
      component: "compliance",
      message: "Add a valid Tax Compliance Certificate.",
      points_gain: 8,
      action: "Upload your TCC.",
    },
  ],
  data_confidence: "low",
  config_version: "1.0.0",
  computed_at: "2025-03-04T10:00:00Z",
};

describe("ScoreDisplay", () => {
  it("shows the deterministic rubric and the not-a-credit-score disclaimer", () => {
    render(<ScoreDisplay assessment={assessment} disclaimer="Example disclaimer." />);

    expect(screen.getByText("62")).toBeInTheDocument();
    expect(screen.getByText("Developing")).toBeInTheDocument();
    expect(screen.getByText("Cash flow")).toBeInTheDocument();
    expect(screen.getByText("Add a valid Tax Compliance Certificate.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "This score is a transparent rubric based on common lending criteria. It is not a credit score and does not guarantee funding.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Low data confidence: add a confirmed M-Pesa statement.")).toBeInTheDocument();
    expect(screen.getByText("Example disclaimer.")).toBeInTheDocument();
  });
});

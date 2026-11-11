import { expect, test } from "@playwright/test";

const user = {
  id: "8a6f0f8e-1c2a-4a4a-9a9a-000000000001",
  email: "merchant@example.com",
  phone: "+254700000000",
  role: "merchant",
  email_verified: true,
  onboarding_step: 4,
  onboarding_percent: 100,
  consent_version: "m1-v1",
  consent_at: "2025-03-04T10:00:00Z",
};

const readiness = {
  latest: {
    id: "assessment-1",
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
    ],
    gaps: [],
    data_confidence: "medium",
    config_version: "1.0.0",
    computed_at: "2025-03-04T10:00:00Z",
  },
  history: [],
  disclaimer: "This is a rule-based rubric, not a credit score.",
};

test("merchant logs in and sees readiness plus matches", async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path.endsWith("/auth/login")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user, access: "test-access-token" }),
      });
      return;
    }
    if (path.endsWith("/auth/csrf")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ csrfToken: "csrf-test" }),
      });
      return;
    }
    if (path.endsWith("/me")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      });
      return;
    }
    if (path.endsWith("/business")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "business-1",
          name: "Mama Njeri Shop",
          trading_name: "",
          sector: "retail",
          what_they_sell: "Groceries",
          county: "Nairobi",
          town: "Kawangware",
          started_on: "2021-01-01",
          structure: "sole_proprietor",
          employee_band: "1-5",
          owner_name: "Njeri Wambui",
          owner_phone: "+254700000000",
          onboarding_percent: 100,
          years_operating: 4.2,
        }),
      });
      return;
    }
    if (path.endsWith("/readiness")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(readiness),
      });
      return;
    }
    if (path.endsWith("/financials/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          has_statement: true,
          months_of_data: 6,
          average_monthly_inflow: "120000",
          average_monthly_outflow: "80000",
          revenue_consistency_cv: 0.18,
          data_confidence: "medium",
        }),
      });
      return;
    }
    if (path.endsWith("/opportunities/matches")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "match-1",
            fit_level: "strong",
            state: "new",
            computed_at: "2025-03-04T10:00:00Z",
            explanation: {
              summary: "You meet the main requirements.",
              met: [],
              missing: [],
              moves_to_strong: [],
              score_gap: 0,
            },
            opportunity: {
              id: "op-1",
              name: "EXAMPLE — working capital loan",
              provider: "EXAMPLE — provider",
              provider_type: "mfi",
              type: "loan",
              description: "Working capital for small shops.",
              min_amount: "10000",
              max_amount: "500000",
              min_months_operating: 12,
              min_readiness_score: 50,
              allowed_sectors: [],
              counties: [],
              required_compliance: [],
              required_documents: [],
              accepts_informal: true,
              application_url: "",
              deadline: null,
              last_verified_at: "2025-03-04T10:00:00Z",
              notes: "",
            },
          },
        ]),
      });
      return;
    }
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "Not found." } }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Email address").fill("merchant@example.com");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Your readiness" })).toBeVisible();
  await expect(page.getByRole("img", { name: "62 out of 100" })).toBeVisible();
  await expect(page.getByText("EXAMPLE — working capital loan")).toBeVisible();
});

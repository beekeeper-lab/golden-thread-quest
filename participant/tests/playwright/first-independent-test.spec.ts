import { expect, test } from "@playwright/test";
import { PassportPage } from "./pages/example-page";

/*
 * Business risk: a participant's own claims inflate the record a reviewer and a manager
 * trust. The product's rule is that only a reviewer's approval earns verified XP; work the
 * participant has finished but no reviewer has approved counts as claimed, and stays
 * visibly separate.
 *
 * Test data (fixtures/participant/progress.yaml, copied fresh for each run by
 * serve-fixture.mjs, so the participant's own progress is never read or changed):
 *   - Alex Rivera, on the Golden Thread Foundations track.
 *   - Base Camp "Establish a Safe Local Quest Repository", 20 XP: verified (reviewer approved).
 *   - Jira "Synchronize My Assigned Jira Stories", 30 XP: evidence ready, never reviewed.
 *
 * So the expected passport is: 50 claimed XP (20 + 30), 20 verified XP (Base Camp only),
 * and Jira Jungle showing one claimed quest and no verified quest.
 */

test(
  "passport counts only reviewer-approved work as verified XP and keeps unreviewed work as claimed",
  { tag: ["@feature-passport", "@risk-high", "@read-only", "@duration-fast"] },
  async ({ page }, testInfo) => {
    const passport = new PassportPage(page);
    await passport.open();

    // The reviewer-approved Base Camp quest is the only verified work.
    await expect(passport.total("Verified XP")).toHaveText("20");
    await expect(passport.total("Verified quests")).toHaveText("1");

    // The unreviewed Jira quest still counts as the participant's claim.
    await expect(passport.total("Claimed XP")).toHaveText("50");

    // And its region shows it as claimed and evidence-ready, not verified.
    await expect(passport.regionCounts("Jira Jungle")).toHaveText(
      "Claimed: 1 · Verified quests: 0",
    );
    await expect(passport.regionStates("Jira Jungle")).toContainText("1 evidence ready");

    // Success evidence, taken once, at the point the business rule has been shown.
    const shot = testInfo.outputPath("validated-state.png");
    await passport.progress.screenshot({ path: shot });
    await testInfo.attach("validated-state", { path: shot, contentType: "image/png" });
  },
);

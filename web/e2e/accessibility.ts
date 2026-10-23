import { expect, type Page } from "@playwright/test";
import axe from "axe-core";

export async function auditAccessibility(page: Page) {
  await page.addScriptTag({ content: axe.source });
  const result = await page.evaluate(async () => {
    const engine = (window as unknown as { axe: typeof axe }).axe;
    function luminance(color: string) {
      return color.match(/\d+/g)!.slice(0, 3).map(value => Number(value) / 255)
        .map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
        .reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    }
    const controlContrast = [...document.querySelectorAll("main select, main textarea")].map(node => {
      const style = getComputedStyle(node);
      const border = luminance(style.borderTopColor);
      return [style.backgroundColor, getComputedStyle(document.body).backgroundColor].map(background => {
        const value = luminance(background);
        return (Math.max(border, value) + 0.05) / (Math.min(border, value) + 0.05);
      });
    }).flat();
    const result = await engine.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] },
    });
    // Never forward raw DOM, account names, or authentication state to logs.
    return {
      violations: result.violations.map(rule => ({ id: rule.id, impact: rule.impact, nodes: rule.nodes.length })),
      incomplete: result.incomplete.map(rule => ({ id: rule.id, nodes: rule.nodes.length })),
      controlContrast,
    };
  });
  expect(result.violations, "axe WCAG A/AA and best-practice violations").toEqual([]);
  expect(result.controlContrast.every(ratio => ratio >= 3), "Select/textarea boundaries must contrast with their adjacent backgrounds").toBe(true);
  return result;
}

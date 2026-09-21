import { expect, test } from '@playwright/test';

/**
 * Recruiter journey (Phase 19): Explore → contract → obligation source →
 * assign → audit → search → versions → upload → reset. Runs against a live
 * backend + seeded evaluation workspace (see docs/recruiter-guide.md).
 */
test('recruiter evaluates ClauseRadar without signup', async ({ page }) => {
  // 1. Open site, explore without signup.
  await page.goto('/welcome');
  await expect(page.getByRole('heading', { name: 'ClauseRadar' })).toBeVisible();
  await page.getByRole('button', { name: 'Explore ClauseRadar' }).click();
  await expect(page.getByText('How to evaluate ClauseRadar')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('status').first()).toBeVisible();

  // 2. Open the Vendor Agreement.
  await page.getByRole('link', { name: 'Contracts', exact: true }).click();
  await page.getByRole('link', { name: 'Vendor Master Services Agreement' }).first().click();
  await expect(page.getByRole('heading', { name: 'Vendor Master Services Agreement' })).toBeVisible();

  // 3. Obligations with source evidence exist.
  await expect(page.getByRole('heading', { name: 'Obligations' })).toBeVisible();
  const firstCard = page.locator('section[aria-label="Obligations"] article.card').first();
  await expect(firstCard).toBeVisible();
  await firstCard.getByText('Source evidence', { exact: false }).click();
  await expect(firstCard.locator('blockquote.evidence')).toBeVisible();

  // 4. Assign owner + change priority (permitted mutations).
  const ownerSelect = firstCard.getByLabel('Assign owner');
  await ownerSelect.selectOption({ index: 1 });
  await expect(firstCard.getByText('Owner updated.')).toBeVisible();

  // 5. Audit log records the actions.
  await page.getByRole('link', { name: 'Audit Log', exact: true }).click();
  await expect(page.getByText('obligation.owner_changed').first()).toBeVisible();

  // 6. Search finds insurance across types.
  await page.getByRole('link', { name: 'Search', exact: true }).click();
  await page.getByLabel('Search everything').fill('insurance');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByText(/result\(s\) for/)).toBeVisible();

  // 7. Compare contract versions v1 → v2.
  await page.getByRole('link', { name: 'Contracts', exact: true }).click();
  await page.getByRole('link', { name: 'Vendor Master Services Agreement' }).first().click();
  await expect(page.getByRole('heading', { name: 'Versions' })).toBeVisible();
  await page.getByLabel('Compare from version').selectOption('1');
  await page.getByLabel('Compare to version').selectOption('2');
  await page.getByRole('button', { name: 'Compare', exact: true }).click();
  await expect(page.getByText(/modified/)).toBeVisible();

  // 8. Upload own document and see extracted obligations.
  const fileInput = page.locator('section[aria-label="Documents"] input[type="file"]');
  await fileInput.setInputFiles('e2e/fixtures/sample-contract.pdf');
  await expect(page.getByText(/ready/i).first()).toBeVisible({ timeout: 30_000 });

  // 9. Ask with citations.
  await page.getByRole('link', { name: 'Ask', exact: true }).click();
  await page.getByLabel('Ask a question').fill('What insurance obligations exist?');
  await page.getByRole('button', { name: 'Ask', exact: true }).click();
  await expect(page.getByText('Cited sources')).toBeVisible({ timeout: 30_000 });

  // 10. Reset restores the seed (last — destructive).
  page.once('dialog', (d) => d.accept());
  await page.getByRole('button', { name: 'Reset evaluation workspace' }).click();
  await expect(page.getByText('How to evaluate ClauseRadar')).toBeVisible({ timeout: 60_000 });
});

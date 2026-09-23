import { expect, test } from '@playwright/test';

/**
 * TEMPORARY acceptance spec for the CSRF production fix (deleted after the run).
 * Fresh browser context; real preview deployment; no resets, no uploads.
 *
 * Covers: fresh browser CSRF bootstrap, session-cookie regression, unsafe
 * mutation with X-CSRFToken on the wire, back/forward + direct SPA route
 * navigation through the Django-serving path, and no unexpected 403/errors.
 */
test('csrf acceptance: eval bootstrap, evidence, mutation, session reuse, login, spa nav', async ({
  page,
  context,
}) => {
  const forbidden: string[] = [];
  const consoleErrors: string[] = [];
  page.on('response', (r) => {
    if (r.status() === 403) forbidden.push(`${r.request().method()} ${r.url()}`);
  });
  page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(`console: ${m.text()}`);
  });

  // 1-2. Fresh context, landing page.
  await page.goto('/welcome');
  await expect(page.getByRole('heading', { name: 'ClauseRadar' })).toBeVisible();

  // 3-4. eval/info succeeds and plants the csrftoken cookie.
  const info = await page.request.get('/api/v1/eval/info/');
  expect(info.status()).toBe(200);
  let cookies = await context.cookies();
  expect(cookies.some((c) => c.name === 'csrftoken')).toBe(true);

  // 5-7. Explore: session bootstrap 200, no CSRF failure text.
  await page.getByRole('button', { name: 'Explore ClauseRadar' }).click();
  await expect(page.getByText('How to evaluate ClauseRadar')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('CSRF Failed')).not.toBeVisible();

  // Confirm csrftoken cookie still present after explore.
  cookies = await context.cookies();
  expect(cookies.some((c) => c.name === 'csrftoken')).toBe(true);

  // 8-9. Contracts load; open the Vendor Agreement.
  await page.getByRole('link', { name: 'Contracts', exact: true }).click();
  await page.getByRole('link', { name: 'Vendor Master Services Agreement' }).first().click();
  await expect(page.getByRole('heading', { name: 'Vendor Master Services Agreement' })).toBeVisible();

  // 10-11. Obligation + source evidence load.
  await expect(page.getByRole('heading', { name: 'Obligations' })).toBeVisible();
  const firstCard = page.locator('section[aria-label="Obligations"] article.card').first();
  await expect(firstCard).toBeVisible({ timeout: 60_000 });
  await firstCard.getByText('Source evidence', { exact: false }).click();
  await expect(firstCard.locator('blockquote.evidence')).toBeVisible();

  // 12-13. Mutation with X-CSRFToken header present on the wire.
  const approve = firstCard.getByRole('button', { name: 'Approve' });
  if ((await approve.count()) > 0) {
    const [confirmResponse] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/confirm/') && r.request().method() === 'POST',
        { timeout: 60_000 },
      ),
      approve.first().click(),
    ]);
    expect(confirmResponse.status()).toBe(200);
    expect(confirmResponse.request().headers()['x-csrftoken']).toBeTruthy();
  }

  // Direct SPA route navigation through Django fallback.
  for (const route of ['/obligations', '/risks', '/audit']) {
    await page.goto(route);
    await expect(page).toHaveURL(/(obligations|risks|audit)/);
  }

  // Browser back/forward.
  await page.goBack();
  await expect(page).toHaveURL(/(risks|audit)/);
  await page.goForward();
  await expect(page).toHaveURL(/(audit)/);

  // Refresh after mutations; page must still render, no CSRF failure.
  await page.goto('/contracts');
  await expect(page.getByRole('heading', { name: 'Contracts' })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('CSRF Failed')).not.toBeVisible();

  // 15. Same flow AFTER a session cookie exists (the exact production bug).
  // A registered user keeps a sessionid cookie; GuestOnly redirects authed
  // users away from /register, so plant it via API (like a prior signup),
  // then Explore through the real UI.
  const stamp = Date.now();
  const regEmail = `csrf-acc-${stamp}@example.com`;
  const reg = await page.request.post('/api/v1/auth/register/', {
    data: { email: regEmail, password: 'password123' },
  });
  expect(reg.status()).toBe(201);
  expect((await context.cookies()).some((c) => c.name === 'sessionid')).toBe(true);
  await page.goto('/welcome');
  await page.getByRole('button', { name: 'Explore ClauseRadar' }).click();
  await expect(page.getByText('How to evaluate ClauseRadar')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('CSRF Failed')).not.toBeVisible();

  // 16. Logout then login through the UI (both are session POSTs).
  const logoutBtn = page.getByRole('button', { name: /log ?out/i });
  if ((await logoutBtn.count()) > 0) {
    await logoutBtn.first().click();
  }
  await page.goto('/login');
  await page.getByLabel('Email').fill(regEmail);
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: /^log ?in/i }).click();
  await expect(page.getByText('CSRF Failed')).not.toBeVisible();
  await expect(page.getByText('No workspace yet')).toBeVisible({ timeout: 60_000 });

  // 14+17. No unexpected 403s, no console errors.
  expect(forbidden).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

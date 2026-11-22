import { expect, test, type Page } from '@playwright/test';

// Evidence pack (SPEC Section 10). Run by `make evidence` after `make seed` and
// `make analytics-run`: signs in as synthetic demo users and captures each screen.
const OUT = process.env.EVIDENCE_DIR ?? 'test-results/evidence';
const PASSWORD = process.env.DEMO_PASSWORD ?? 'demo-password';
const DESKTOP = { width: 1280, height: 800 };
const MOBILE = { width: 375, height: 812 };

async function signIn(page: Page, username: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(`${username}@demo.qauym.test`);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Feed' })).toBeVisible();
}

test.use({ viewport: DESKTOP });

test('@evidence figure 5: sign-in screen', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  await page.screenshot({ path: `${OUT}/fig5_login.png` });
});

test('@evidence figure 6: feed, desktop and mobile', async ({ page }) => {
  await signIn(page, 'demo');
  await expect(page.getByRole('article').first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/fig6_feed.png` });

  await page.setViewportSize(MOBILE);
  await expect(page.getByRole('article').first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/fig6_feed_mobile.png` });
});

test('@evidence my communities, community detail and the empty state', async ({ page }) => {
  await signIn(page, 'demo');
  await page.getByRole('link', { name: 'Communities' }).click();
  await expect(page.getByRole('heading', { name: 'My communities' })).toBeVisible();
  await expect(page.getByText(/Inferred by Qauym on/)).toBeVisible();
  await page.screenshot({ path: `${OUT}/communities.png` });

  await page.getByRole('link', { name: /^Community \d+/ }).click();
  await expect(page.getByRole('heading', { name: 'About this inferred community' })).toBeVisible();
  await page.screenshot({ path: `${OUT}/community_detail.png` });

  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'newcomer');
  await page.getByRole('link', { name: 'Communities' }).click();
  await expect(page.getByRole('heading', { name: 'You are not in a community yet' })).toBeVisible();
  await page.screenshot({ path: `${OUT}/communities_empty.png` });
});

test('@evidence admin analytics runs', async ({ page }) => {
  await signIn(page, 'admin');
  await page.getByRole('link', { name: 'Runs' }).click();
  await expect(page.getByRole('heading', { name: 'Analytics runs' })).toBeVisible();
  await expect(page.getByRole('row', { name: /leiden/i }).first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/admin_runs.png` });
});

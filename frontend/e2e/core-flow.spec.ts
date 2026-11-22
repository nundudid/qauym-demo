import { expect, test, type Browser, type Page } from '@playwright/test';

// Core flow (SPEC Section 10): register, post, follow, like, comment in a real browser.
// Usernames are unique per run, so the test can be repeated against the same database.
const run = Date.now().toString(36);
const author = { username: `aru_${run}`, name: `Aru ${run}` };
const reader = { username: `dias_${run}`, name: `Dias ${run}` };
const PASSWORD = 'correct-horse-battery';

async function registerInNewContext(browser: Browser, user: typeof author): Promise<Page> {
  const context = await browser.newContext(); // separate cookies: a separate person
  const page = await context.newPage();
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/); // signed-out visitors are redirected
  await page.getByRole('link', { name: 'Create an account' }).click();

  await page.getByLabel('Email').fill(`${user.username}@example.com`);
  await page.getByLabel('Username').fill(user.username);
  await page.getByLabel('Display name (optional)').fill(user.name);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page.getByRole('heading', { name: 'Feed' })).toBeVisible();
  return page;
}

test('register, post, follow, like and comment', async ({ browser }) => {
  const postText = `Hello from ${author.name}`;
  const commentText = `Nice post, says ${reader.name}`;

  // Register and post.
  const authorPage = await registerInNewContext(browser, author);
  await authorPage.getByLabel('Write a post').fill(postText);
  await expect(authorPage.getByText(`${postText.length} / 1000 characters`)).toBeVisible();
  await authorPage.getByRole('button', { name: 'Post', exact: true }).click();
  await expect(authorPage.getByRole('article').filter({ hasText: postText })).toBeVisible();

  // A second person registers; their feed does not show the post yet.
  const readerPage = await registerInNewContext(browser, reader);
  await expect(readerPage.getByText(postText)).toHaveCount(0);

  // Follow.
  await readerPage.getByRole('link', { name: 'People' }).click();
  await readerPage.getByLabel('Search by username or name').fill(author.username);
  await readerPage.getByRole('button', { name: `Follow ${author.name}` }).click();
  await expect(readerPage.getByRole('button', { name: `Unfollow ${author.name}` })).toBeVisible();

  // The followed author's post now appears in the feed.
  await readerPage.getByRole('link', { name: 'Feed' }).click();
  const post = readerPage.getByRole('article').filter({ hasText: postText });
  await expect(post).toBeVisible();

  // Like.
  await post.getByRole('button', { name: /Like/ }).click();
  const liked = post.getByRole('button', { name: /Liked/ });
  await expect(liked).toHaveAttribute('aria-pressed', 'true');
  await expect(liked).toContainText('1 like');

  // Comment.
  await post.getByRole('button', { name: /Comments/ }).click();
  await post.getByLabel('Add a comment').fill(commentText);
  await post.getByRole('button', { name: 'Comment', exact: true }).click();
  await expect(post.getByRole('region', { name: 'Comments' }).getByText(commentText)).toBeVisible();
  await expect(post.getByRole('button', { name: /Hide comments/ })).toContainText('1 comment');

  // The author sees the like, the comment and the new follower.
  await authorPage.reload();
  const own = authorPage.getByRole('article').filter({ hasText: postText });
  await expect(own.getByRole('button', { name: /Like/ })).toContainText('1 like');
  await own.getByRole('button', { name: /Comments/ }).click();
  await expect(own.getByText(commentText)).toBeVisible();
  await authorPage.getByRole('link', { name: 'My profile' }).click();
  await expect(authorPage.getByText('1 follower')).toBeVisible();

  // Signing out ends the session.
  await authorPage.getByRole('button', { name: 'Sign out' }).click();
  await expect(authorPage).toHaveURL(/\/login$/);
  await authorPage.goto('/');
  await expect(authorPage).toHaveURL(/\/login$/);
});

# Qauym demo script (M1)

Shows the vertical slice: user activity becomes a visible inferred community. It takes under 10 minutes on a fresh clone once the Docker images are built (the first `make up` downloads and builds them, which depends on your connection).

All accounts below are synthetic (`is_synthetic = true`) and exist only in your local database. The password for every demo account is `demo-password`.

| Account | Email | What it shows |
| --- | --- | --- |
| Demo user | `demo@demo.qauym.test` | A member of an inferred community |
| Admin | `admin@demo.qauym.test` | The analytics runs page and the "Run now" button |
| Newcomer | `newcomer@demo.qauym.test` | The empty state for a user with no connections |

## 1. Start (about 2 minutes)

```sh
make up      # database, Valkey, API, web app; applies migrations
make seed    # about 300 synthetic users in 8 planted interest groups, 60 days of activity
```

Open http://localhost:5173.

## 2. Before any analytics run (1 minute)

1. Sign in as the demo user.
2. Open **Communities**. It says nothing has been inferred yet: no result is shown until a run has been validated and published.
3. Open **Feed**. Posts are from followed people, newest first, with no ranking.

## 3. Run the analytics (1 minute)

1. Sign out, then sign in as the admin.
2. Open **Runs** and press **Run now**. (`make analytics-run` does the same from a terminal.)
3. The table shows two rows for the run. Leiden is `published (active)`; Louvain is `succeeded` and is kept only for comparison. Point out the duration, modularity, community count (8, matching the 8 planted groups) and the graph size.
4. Press **Run now** again straight away: no second run starts, because a run for this minute already exists. This is the double-click protection.

## 4. See the inferred community (2 minutes)

1. Sign out, then sign in as the demo user and open **Communities**.
2. Point out:
   - the **Inferred** label and the snapshot time ("Inferred by Qauym on …");
   - the name "Community _n_" followed by up to three shared interests, each declared by at least 3 members;
   - **People you know in it**: only people the demo user follows or who follow them are named;
   - "Plus _n_ other members": everyone else is counted, not named.
3. Click the community name for the detail page, which adds how much of the user's activity stays inside the community.

## 5. The empty state (1 minute)

Sign out, then sign in as the newcomer and open **Communities**. This user has no follows or interactions, so they are not a node in the graph. The page says so, shows when communities were last inferred, and links to **People**.

## 6. Activity changes the next result (2 minutes)

1. Still as the newcomer, open **People**, search for `aru`, and follow two or three people. Like one of their posts from their profile.
2. Open **Communities**: still the empty state, because results change only when a run is published.
3. Sign in as the admin, wait until the clock passes the minute of the last run, and press **Run now**.
4. Sign in as the newcomer again: **Communities** now shows an inferred community with the people they followed listed under "People you know in it".

## 7. A failed run keeps the previous result (optional, 1 minute)

```sh
docker compose run --rm api pytest tests/test_publication_failure.py -v
```

`test_fr07_injected_failure_keeps_the_previous_result_active` raises an exception after the memberships are inserted and checks that the previous run is still the active one and that no partial memberships are visible.

## Reset

```sh
make seed            # replaces the synthetic data; accounts you registered yourself are kept
make down            # stop everything
docker compose down -v   # also delete the database volume
```

## If something goes wrong

- **A port is in use:** copy `.env.example` to `.env` and change `API_PORT` or `WEB_PORT`.
- **"Too many attempts" when signing in:** sign-in is limited to 10 attempts per minute per IP; wait a minute.
- **"No new run started":** a run already exists for the current minute; wait until the next minute.

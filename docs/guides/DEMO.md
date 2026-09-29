# Demo Walkthrough

About fifteen minutes. You play all three roles: participant, reviewer and curriculum
maintainer. You work in a throwaway clone, so nothing here touches your working copy.

Every command is one line. Run them from the clone's folder unless a step says otherwise.
The sample files you copy in are in `docs/guides/demo/`.

## 0. Set up (terminal 1)

1. `git clone https://github.com/beekeeper-lab/golden-thread-quest ~/gtq-demo`
2. `cd ~/gtq-demo`
3. `make setup`
4. `make serve`
5. Open <http://127.0.0.1:8765/>. The home page recommends **Establish a Safe Local Quest
   Repository**, with 0 claimed XP and 0 verified XP.

Leave terminal 1 running. Use a second terminal for the file steps, and run
`cd ~/gtq-demo` in it first.

## 1. Participant: start, and submit too early

1. Click **View quest** on the recommendation. Read the quest page: mission, numbered
   acceptance criteria, and **Required evidence**, where every item says *Not detected*.
2. Under **Status and actions**, tick the confirmation box, click **Start quest**, and accept
   the browser's confirmation. An evidence package now exists under
   `participant/evidence/base-camp-repository-safety/base-attempt-001/`.
3. Click **Open evidence workspace**, then **Run the repository foundation check**. It
   passes with an advisory: `PROOF.md` is still empty.
4. Click **Mark evidence ready**, then **Record local validation**, then tick the box and
   click **Submit for review**. The totals beside the navigation now show **20 claimed XP** and
   **0 verified XP**:
   your claim and the reviewer's verification are counted separately.

The application let you submit with three required files missing. A reviewer sees that, and
the next step is what a reviewer should do about it.

## 2. Reviewer: ask for changes

1. Click **Reviewer** in the navigation (behind **Menu** on a narrow window), then the quest. The **Required evidence**
   checklist shows three items *Not detected*.
2. In the decision form: enter a name, choose **Needs changes**, and fill in one finding with
   a severity, a summary, the evidence you saw, a criterion and the change you require.
   Tick the confirmation box, click the button and accept.

## 3. Participant: fix and resubmit (terminal 2)

1. `mkdir -p participant/context participant/evidence/base-camp-repository-safety/base-attempt-001/logs`
2. `cp docs/guides/demo/repository-ownership.md docs/guides/demo/audit-log.md participant/context/`
3. `cp docs/guides/demo/second-run.txt participant/evidence/base-camp-repository-safety/base-attempt-001/logs/`
4. `cp docs/guides/demo/PROOF.md participant/evidence/base-camp-repository-safety/base-attempt-001/PROOF.md`
5. In the browser, open **Evidence** and the quest. The reviewer's finding is at the top. The
   three files still say *Not detected*: the page is from the last build, and the next
   action rebuilds it. Click **Resume after review**, then **Run the repository foundation check**, then
   **Mark evidence ready**, **Record local validation** and **Submit for review**. Every
   required item now says *Detected* or *Validated*.

## 4. Reviewer: approve

1. **Reviewer**, then the quest. Enter a name, choose **Approve**, and write a verification
   statement of at least twenty characters saying what you checked. Tick the confirmation
   box and submit.
2. Open **Passport**. It shows 20 verified XP and 1 verified quest. The home page now
   recommends a quest in the next region.

## 5. Maintainer: add a quest without touching UI code

1. Stop the service in terminal 1 with Ctrl-C.
2. `cp docs/guides/demo/retro-actions.md content/quests/scrum-village/`
3. `git status --short content templates quest_app assets` shows one new file and nothing
   else.
4. `make serve`, then open **Catalog** and type `retrospective` in the search box. **Track
   Retrospective Actions to Closure** appears. It also appears on the Scrum Village region
   page and on a new `retrospective` tag page.

## 6. Failure: broken content never replaces a good site (terminal 2)

1. `sed -i 's/^region: scrum-village/region: scrum-vilage/' content/quests/scrum-village/retro-actions.md`
2. `make build` fails. It names the file and the `region` field, lists the valid regions and
   asks "Did you mean 'scrum-village'?".
3. Reload the browser. The site still works, with the last good build.
4. `cp docs/guides/demo/retro-actions.md content/quests/scrum-village/` then `make build`
   succeeds again.

## Clean up

1. Ctrl-C in terminal 1.
2. `rm -rf ~/gtq-demo`

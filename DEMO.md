# Demo video script (under 3 minutes)

Record the browser at http://localhost:8000 with the terminal hidden. Run each search once **before** recording so it's
cached: the demo then loads instantly and costs no searches.

Pre-cache:

```bash
python cli.py ManthanNimodiya --query "software engineer intern" --location "Bengaluru, Karnataka, India" --companies 6
python cli.py ManthanNimodiya --query "software engineer intern remote" --location India --companies 6
```

---

**0:00 to 0:20. The problem**

"I'm a second-year student in Bengaluru. Last week I emailed nearly 50 companies about internships by hand. Most of the time
didn't go on writing. It went on finding listings that weren't job-board reposts, checking whether a company was a
startup, finding an email they'd actually published, and working out which of my pull requests mattered for each role."

**0:20 to 0:40. The idea**

"Internship Scout does those four steps for any student with a GitHub account. Your merged pull requests are your CV."

**0:40 to 1:30. Run it**

- Type your GitHub username. Click the **Bengaluru SWE intern** chip and choose 6 companies. Click **Find internships**.
- Point at the profile line: "It read my merged PRs in other people's projects and worked out my real languages."
- Point at the status line: "It searched Google Jobs through SerpApi and skipped reposts from job boards."

**1:30 to 2:20. One result**

- Open the top result (FLAM in my test run). Read two or three of the reasons aloud.
- "The founding year comes with its source, and it's only used if it clearly belongs to the same company."
- "The email is only taken from the company's own site, here its own careers page, and support or customer-care inboxes are skipped."
- Open **Draft email**: "It picked my most relevant fix from each project, not just my latest PR. Nothing is sent for me: I edit it and send it myself."

**2:20 to 2:45. Searches are scarce**

- Point at the budget line: "The free plan has 250 searches a month. Everything is cached, so running this again costs nothing."
- Click **Download as CSV**: "And this becomes my outreach tracker."

**2:45 to 3:00. Close**

"Google Jobs finds the listings, Google Search checks the company, and Google News adds funding signals. All three come
through SerpApi. Internship Scout turns that data into a shortlist and a first email a student can actually send.
Thanks for watching."

# Tandoori Masala Sales Dashboard

**🔗 Live dashboard: [dashboardnorrebro.streamlit.app](https://dashboardnorrebro.streamlit.app/)** (password-protected)

## What this is

I built this for my workplace in Nørrebro, Copenhagen, to
replace manual end-of-day spreadsheet math with something the whole team
can check at a glance.

We take orders through our own till (Tillty), plus Wolt and UberEats.
Every day, someone closes out the register, counts tips and cash, and
logs it. This dashboard turns that daily log into live charts — revenue
by channel, tips and cash by staff member, and a record of who worked
which hours — and updates automatically as new data comes in. Anyone on
the team can open the link above from their phone or laptop, no
spreadsheet software required.

It's a small project, but a genuinely useful one: fewer manual totals,
fewer "wait, how much cash did we actually have Tuesday?" conversations,
and a much faster way to see which channel is actually driving revenue.

## How I built it

- **Streamlit** for the dashboard itself — Python, so I could reuse
  pandas for the data cleaning and Plotly for the charts.
- **Google Drive** holds the actual Excel file, accessed through a
  Google service account, so the data source is the same spreadsheet
  format the whole team already understands — no separate database.
- **Streamlit Community Cloud** hosts the app itself, so it's always on
  and reachable from a permanent link, independent of any one laptop.
- Two in-app forms (daily sales entry, staff working hours) write
  straight back to the Drive file, so the dashboard and the spreadsheet
  never fall out of sync.

## Setup reference (for running your own copy)

The rest of this README is technical setup notes, mostly so future-me
remembers how the pieces fit together.

### 1. Google Drive access (service account — supports writing, not just reading)

1. Put your Excel file in a Google Drive folder (the Google Drive desktop
   app can sync it automatically like a normal folder on your Mac).
2. Get the **File ID**: right-click the file → Share → copy the link. It
   looks like `https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view`
   — the part between `/d/` and `/view` is your File ID.
3. Go to https://console.cloud.google.com and create a new project (or
   use an existing one).
4. In the search bar, find **"Google Drive API"** and click **Enable**.
5. Go to **APIs & Services → Credentials → Create Credentials → Service
   Account**. Give it any name (e.g. "sales-dashboard-bot") and finish
   the wizard.
6. Click into the new service account → **Keys** tab → **Add Key →
   Create new key → JSON**. This downloads a `.json` file — keep it
   private, never commit it to GitHub.
7. Open that JSON file and copy the `client_email` value (looks like
   `xxxx@xxxx.iam.gserviceaccount.com`).
8. Back in Google Drive, right-click your Excel file → **Share** → paste
   that email address → set its role to **Editor** → Send/Share.

### 2. Convert the JSON key into your secrets file

Your downloaded JSON key has fields like `type`, `project_id`,
`private_key`, `client_email`, etc. These map directly into a
`[gcp_service_account]` section of your secrets — see
`.streamlit/secrets.toml.example` for the exact format to copy from.
The trickiest part is `private_key`: keep its `\n` line breaks by wrapping
the whole value in triple quotes (`"""`) as shown in the example.

### 3. Put this code on GitHub

Create a repository and upload `app.py`, `config.py`, `drive_utils.py`,
`requirements.txt`, and `.gitignore`. Never upload a real
`.streamlit/secrets.toml` — the `.gitignore` already excludes it.

### 4. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. "New app" → pick the repository → main file `app.py`.
3. Under "Advanced settings" → Secrets, paste `APP_PASSWORD`,
   `GOOGLE_DRIVE_FILE_ID`, and the full `[gcp_service_account]` block.
4. Deploy. You'll get a permanent link — that's what you share with
   other people; they'll be asked for the password first.

### 5. Testing locally before deploying (optional)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with real values
streamlit run app.py
```

### Notes

- If the dashboard shows stale data, click **🔄 Refresh now** — it
  force-clears the cache instead of waiting for the ~60-second
  auto-refresh.
- If you rename or re-upload the Excel file on Drive, double-check the
  File ID hasn't changed (re-copy the share link if the dashboard errors).

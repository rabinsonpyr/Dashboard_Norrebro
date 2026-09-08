# Sales Dashboard — Cloud Version

An always-on, password-protected dashboard with a permanent link, reading
your Excel data from Google Drive. Updates automatically within about a
minute of you saving changes — no restart needed, works even when your
Mac is off.

## How it works

- You keep editing the Excel file exactly as before — just save it inside
  a synced Google Drive folder instead of (or in addition to) locally.
- The app is hosted on Streamlit Community Cloud (free), so it's always
  running, independent of your laptop.
- The app re-fetches the file from Google Drive every ~60 seconds, so any
  edit you save shows up shortly after, for everyone with the link.
- A simple password screen gates the whole dashboard.

## 1. Set up Google Drive access (service account — supports writing, not just reading)

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
   (You can now turn off "Anyone with the link" if it was on before —
   only the service account and people you explicitly add can access it.)

## 2. Convert the JSON key into your secrets file

Your downloaded JSON key has fields like `type`, `project_id`,
`private_key`, `client_email`, etc. These map directly into a
`[gcp_service_account]` section of your secrets — see
`.streamlit/secrets.toml.example` for the exact format to copy from.
The trickiest part is `private_key`: keep its `\n` line breaks by wrapping
the whole value in triple quotes (`"""`) as shown in the example.

## 2. Put this code on GitHub

1. Create a free GitHub account if you don't have one: https://github.com
2. Create a new repository (e.g. `sales-dashboard`), and upload these
   files to it: `app.py`, `config.py`, `requirements.txt`, `.gitignore`.
   (Do **not** upload `.streamlit/secrets.toml` if you create one — the
   `.gitignore` already excludes it.)

## 3. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with your GitHub account.
2. Click **"New app"**, pick your repository, and set the main file to
   `app.py`.
3. Before clicking Deploy, open **"Advanced settings" → Secrets** and paste
   your `APP_PASSWORD`, `GOOGLE_DRIVE_FILE_ID`, and the entire
   `[gcp_service_account]` block from your local `secrets.toml` (see step 2
   above).
4. Click **Deploy**. After a minute or two you'll get a permanent link like:
   ```
   https://your-app-name.streamlit.app
   ```

That link is what you share with other people. They'll be asked for the
password you set above before seeing anything.

## 4. Updating the password or file later

Go to your app on https://share.streamlit.io → **⋮ menu** → **Settings**
→ **Secrets**, edit the values, and save — the app restarts automatically
with the new settings.

## 5. Testing locally before deploying (optional)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with real values
streamlit run app.py
```

## Notes

- Your old local automation (`launchd`, `run_dashboard.sh`) is no longer
  needed for this cloud version — the app refreshes itself. You can keep
  using the old local version too if you still want a version that opens
  automatically on your own Mac at a fixed time.
- If the dashboard shows stale data, click the **🔄 Refresh now** button
  at the top — it force-clears the cache instead of waiting for the
  60-second auto-refresh.
- If you rename or re-upload the Excel file on Drive, the File ID usually
  stays the same as long as it's the same Drive file (not a new upload) —
  but double-check by re-copying the share link if the dashboard errors.

# Main and support app shortcuts

Use the Download button on the normal site to install **Gather & Gift**, which launches `/`.

Open `https://gather-gift.onrender.com/support/login` in your browser for **Download Support**. It installs **Gather & Gift Support**, which launches `/support/login`. This support download button is shown only on that login page. Staff signing out return to support login.

The two manifests have distinct IDs, so compatible browsers can recognize separate installations. The support manifest uses `/support` as its navigation scope. Browser/platform installation support varies; the download dialog includes Chrome/Edge and Safari/iPad instructions. See [manifest IDs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/id).

These are two web-app shortcuts to the same service, not separate accounts or isolated browser profiles. Cookies and browser storage can be shared on the same origin. Installing the support shortcut grants no privileges; staff must authenticate through the dedicated support login.

## Create the master support/developer account

From the local project root, where `.env` selects the shared Railway database:

```powershell
.\.venv\Scripts\python.exe -m flask --app app create-superuser
```

Enter a new email address, display name, and a unique password of at least 16 characters. Password input is hidden. The command creates an account with both `is_support` and `is_superuser` enabled, granting the master support and developer permissions. No account is created by installing a shortcut. If a master already exists, the command refuses to create another; sign in with that master account instead.

On Render Shell, use `flask --app backend create-superuser`. The local command above loads the project's `.env`; Render uses its own environment settings. Do not put passwords in command-line arguments or GitHub files.

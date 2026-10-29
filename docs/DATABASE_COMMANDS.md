# Database commands from the terminal

Run these from the project folder. The commands use `.venv` Python when present, otherwise an installed Python. The npm commands load the root `.env` with priority over stale terminal environment variables. The database does not have to be hosted on the same service as the app.

Apply all existing migrations (including creating tables in an empty database):

```powershell
npm.cmd run db:upgrade
```

Check the connected database's current revision:

```powershell
npm.cmd run db:current
```

When changing or adding models in `backend/app/models/__init__.py`:

```powershell
npm.cmd run db:migrate -- --message "Add my new table"
# Review the generated file under backend/migrations/versions before applying it.
npm.cmd run db:upgrade
npm.cmd run db:check
```

`db:migrate` creates a migration file; `db:upgrade` applies it. A React UI change by itself does not define a database table. Review generated migrations, especially renames and dropped columns/tables, and back up databases containing important data before schema changes.

These commands affect whichever database `DATABASE_URL` selects. If `.env` points to Railway, they affect Railway, even though you run them on your laptop. This project now intentionally uses one shared Railway database for local manual testing and deployment. Changes made locally affect that shared data. Automated tests continue to use isolated temporary databases. Commit migration files, push them to GitHub, and Render's pre-deploy command will apply them to Render's configured database. Never commit `.env` or database credentials.

`npm.cmd run db:heads` displays the available migration head without querying database records. The equivalent standard command is `python -m flask --app backend db upgrade` after activating the virtual environment. Render continues using its own environment settings, independently of the local `.env`.

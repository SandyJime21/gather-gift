# App versions

The version in `package.json` appears in the site footer, including the developer portal, and below the sign-in and registration forms.

- 3.0.0: Theme inspiration, editable hex colors, browser-saved favorite palettes, undo/reset, readable text suggestions, and visible app versions.
- 0.1.0: Previously recorded package version. Earlier numbered releases could not be verified.

To save a new numbered source snapshot and update the displayed version:

```sh
npm run release -- 3.0.1
npm run build
```

Each release goes into `release/<version>/` and includes the current source files, including uncommitted changes. Existing snapshots cannot be overwritten. Dependencies, ignored files, credentials, databases, and generated builds are excluded. Snapshots are local and ignored by Git; copy them to your backup location for safekeeping. This command does not deploy the app or back up live data.

Use a new version for each release and add its changes to this history before running the command. To restore a snapshot, copy it into a separate folder, install dependencies, configure the environment, and build it.

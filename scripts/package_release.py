"""Build a clean source bundle for GitHub without local family data."""
from zipfile import ZipFile, ZIP_DEFLATED
from release_check import ROOT, source_files, main as check


def main():
    check()
    folders = {'src', 'public', 'backend', 'scripts', '.github', 'docs'}
    top_files = {'.gitignore', '.gitattributes', '.dockerignore', '.env.example',
                 'Dockerfile', 'render.yaml', 'docker-compose.yml', 'package.json',
                 'package-lock.json', 'vite.config.js', 'index.html', 'app.py',
                 'README.md', 'ARCHITECTURE.md', 'IMPLEMENTATION_PLAN.md', 'schema.sql', 'mysql.sql'}
    target = ROOT / 'release' / 'gather-gift-source.zip'
    target.parent.mkdir(exist_ok=True)
    count = 0
    with ZipFile(target, 'w', compression=ZIP_DEFLATED) as bundle:
        for path in sorted(source_files()):
            relative = path.relative_to(ROOT)
            if relative.parts[0] not in folders and relative.as_posix() not in top_files:
                continue
            if path.name.endswith(('-results.json', '-results.xml')):
                continue
            if path.is_file():
                bundle.write(path, relative.as_posix())
                count += 1
    print(f'Created {target.relative_to(ROOT)} with {count} source files; no local account data.')


if __name__ == '__main__':
    main()

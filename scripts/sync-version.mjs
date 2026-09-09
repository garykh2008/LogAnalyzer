// Keeps src-tauri/Cargo.toml aligned with package.json, the version source of
// truth (tauri.conf.json reads package.json directly, and the UI gets the
// version injected via vite `define`). Runs as the npm `version` lifecycle
// hook, so `npm version 3.2.0` bumps the whole tree in one shot.
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const cargoTomlPath = join(root, 'src-tauri', 'Cargo.toml');

const version = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8')).version;

const toml = readFileSync(cargoTomlPath, 'utf8');
const updated = toml.replace(
  /^(\[package\][\s\S]*?^version = ")[^"]+"/m,
  `$1${version}"`,
);

if (updated === toml && !toml.includes(`version = "${version}"`)) {
  console.error('sync-version: could not find [package] version in Cargo.toml');
  process.exit(1);
}

writeFileSync(cargoTomlPath, updated);

// Refresh the lockfile entry so `cargo` doesn't rewrite it on the next build.
try {
  execFileSync('cargo', ['update', '-p', 'loganalyzer', '--offline'], {
    cwd: join(root, 'src-tauri'),
    stdio: 'pipe',
  });
} catch {
  // Offline metadata refresh is best-effort; a normal build fixes the lock.
}

// Stage so npm's auto-commit includes the Rust side. Best-effort: failing to
// stage must not abort `npm version` halfway through.
try {
  execFileSync('git', ['add', 'src-tauri/Cargo.toml', 'src-tauri/Cargo.lock'], { cwd: root });
} catch {
  console.warn(`sync-version: could not git-add — stage src-tauri/Cargo.toml and Cargo.lock manually (-> ${version})`);
}

console.log(`sync-version: Cargo.toml/Cargo.lock -> ${version}`);

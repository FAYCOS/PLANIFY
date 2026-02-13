const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const tauriDir = path.join(root, 'desktop');
const confPath = path.join(tauriDir, 'src-tauri', 'tauri.conf.json');

if (!fs.existsSync(confPath)) {
  console.error('tauri.conf.json introuvable. Lance d\'abord setup_tauri.sh');
  process.exit(1);
}

const conf = JSON.parse(fs.readFileSync(confPath, 'utf8'));

conf.build = conf.build || {};
conf.build.beforeDevCommand = conf.build.beforeDevCommand || "python3 run.py";
conf.build.devPath = conf.build.devPath || "http://127.0.0.1:5000";
conf.build.beforeBuildCommand = conf.build.beforeBuildCommand || "";
conf.build.distDir = conf.build.distDir || "../static";

conf.tauri = conf.tauri || {};
conf.tauri.allowlist = conf.tauri.allowlist || {};
conf.tauri.allowlist.shell = { all: false, open: false, execute: false };

conf.tauri.bundle = conf.tauri.bundle || {};
conf.tauri.bundle.externalBin = conf.tauri.bundle.externalBin || [
  "../sync_daemon.py",
  "../run.py"
];

conf.tauri.windows = [
  {
    title: "Planify",
    width: 1280,
    height: 800,
    resizable: true
  }
];

fs.writeFileSync(confPath, JSON.stringify(conf, null, 2));
console.log('tauri.conf.json patché');

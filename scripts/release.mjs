import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root=path.resolve(import.meta.dirname,'..');
const requested=process.argv[2];
if(requested&&!/^\d+\.\d+\.\d+$/.test(requested))throw Error('Use a version such as 0.2.1');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
const pkg=read('package.json'),version=requested||pkg.version;
const destination=path.join(root,'release',version);
if(fs.existsSync(destination))throw Error(`Version ${version} already has a saved snapshot. Choose a new version.`);
// Include current tracked and untracked source, respecting repository ignores.
const files=execFileSync('git',['ls-files','--cached','--others','--exclude-standard','-z'],{cwd:root,encoding:'utf8'}).split('\0').filter(Boolean).filter(file=>!/(^|\/)(\.env(?:\..*)?|\.git|\.aws|\.codex|\.agents|node_modules|instance|release|dist)(\/|$)|\.(pem|key|p12|pfx|sqlite|db|log|eml)$/i.test(file));
if(requested){
 pkg.version=version;
 const lock=read('package-lock.json');lock.version=version;lock.packages[''].version=version;
 fs.writeFileSync(path.join(root,'package.json'),JSON.stringify(pkg,null,2)+'\n');
 fs.writeFileSync(path.join(root,'package-lock.json'),JSON.stringify(lock,null,2)+'\n');
}
fs.mkdirSync(destination,{recursive:true});
for(const file of files){const source=path.join(root,file);if(!fs.existsSync(source)||!fs.lstatSync(source).isFile())continue;const target=path.join(destination,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(source,target);}
fs.writeFileSync(path.join(destination,'RELEASE.json'),JSON.stringify({version,savedAt:new Date().toISOString(),commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),description:'Source snapshot includes current working files; install dependencies and configure secrets separately.'},null,2)+'\n');
console.log(`Saved app v${version} to ${destination}`);

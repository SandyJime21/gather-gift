import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {spawnSync} from 'node:child_process';

const root=dirname(dirname(fileURLToPath(import.meta.url)));
const [command,...args]=process.argv.slice(2);
if(!['upgrade','migrate','current','check','heads'].includes(command)){
  console.error('Use db:upgrade, db:migrate, db:current, db:check, or db:heads.');
  process.exit(1);
}
const local=join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const candidates=[...(process.env.PYTHON?[[process.env.PYTHON]]:[]),...(existsSync(local)?[[local]]:[]),['python'],['python3'],...(process.platform==='win32'?[['py','-3']]:[])];
const python=candidates.find(([executable,...prefix])=>spawnSync(executable,[...prefix,'-c','import sys; assert sys.version_info >= (3, 11)'],{cwd:root,windowsHide:true,stdio:'ignore',timeout:10000}).status===0);
if(!python){
  console.error('Python was not found. Activate your Python virtual environment or set PYTHON to its executable path.');
  process.exit(1);
}
console.log('Using the database configured for this project. Connection credentials are not displayed.');
const [executable,...prefix]=python;
const result=spawnSync(executable,[...prefix,'-m','flask','--app','backend','db',command,...args],{cwd:root,windowsHide:true,stdio:'inherit',env:{...process.env,FLASK_SKIP_DOTENV:'0'}});
if(result.error)console.error('Could not start Flask. Install backend/requirements.txt in your Python environment.');
process.exit(result.status??1);

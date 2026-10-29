import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {spawnSync} from 'node:child_process';

export const root=dirname(dirname(fileURLToPath(import.meta.url)));

export function runPython(args){
  const local=join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  const candidates=[...(process.env.PYTHON?[[process.env.PYTHON]]:[]),...(existsSync(local)?[[local]]:[]),['python'],['python3'],...(process.platform==='win32'?[['py','-3']]:[])];
  const python=candidates.find(([executable,...prefix])=>spawnSync(executable,[...prefix,'-c','import sys; assert sys.version_info >= (3, 11)'],{cwd:root,windowsHide:true,stdio:'ignore',timeout:10000}).status===0);
  if(!python){
    console.error('Python was not found. Activate your virtual environment or set PYTHON to its executable path.');
    process.exit(1);
  }
  const [executable,...prefix]=python;
  const result=spawnSync(executable,[...prefix,...args],{cwd:root,windowsHide:true,stdio:'inherit',env:process.env});
  if(result.error)console.error('Could not start Python. Install backend/requirements.txt in your Python environment.');
  process.exit(result.status??1);
}

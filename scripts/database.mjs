import {runPython} from './python.mjs';

const [command,...args]=process.argv.slice(2);
if(!['upgrade','migrate','current','check','heads'].includes(command)){
  console.error('Use db:upgrade, db:migrate, db:current, db:check, or db:heads.');
  process.exit(1);
}
console.log('Using the database configured for this project. Connection credentials are not displayed.');
runPython(['-c',"from dotenv import load_dotenv; load_dotenv('.env', override=True); from flask.cli import main; main()",'--app','backend','db',command,...args]);

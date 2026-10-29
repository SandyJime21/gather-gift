import {useEffect,useState} from 'react';
import {Alert,Button,Modal} from 'react-bootstrap';

export default function InstallApp(){
 const [prompt,setPrompt]=useState(null),[open,setOpen]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [installed,setInstalled]=useState(()=>Boolean(window.matchMedia?.('(display-mode: standalone)').matches || navigator.standalone));
 useEffect(()=>{
  const media=window.matchMedia?.('(display-mode: standalone)');
  const sync=()=>setInstalled(Boolean(media?.matches || navigator.standalone));
  const ready=event=>{event.preventDefault();setPrompt(event);};
  const done=()=>{setInstalled(true);setPrompt(null);setOpen(false);};
  window.addEventListener('beforeinstallprompt',ready);window.addEventListener('appinstalled',done);media?.addEventListener?.('change',sync);
  return()=>{window.removeEventListener('beforeinstallprompt',ready);window.removeEventListener('appinstalled',done);media?.removeEventListener?.('change',sync);};
 },[]);
 async function install(){
  if(!prompt)return;
  setBusy(true);setError('');
  try{await prompt.prompt();const choice=await prompt.userChoice;if(choice.outcome==='accepted')setOpen(false);}catch{setError('Use your browser menu to add Gather & Gift instead.');}finally{setPrompt(null);setBusy(false);}
 }
 if(installed)return null;
 const ipad=/iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1);
 return <><Button variant="outline-success" size="sm" className="install-app-button" onClick={()=>setOpen(true)}>Download</Button><Modal show={open} onHide={()=>setOpen(false)} centered><Modal.Header closeButton><Modal.Title>Download Gather &amp; Gift</Modal.Title></Modal.Header><Modal.Body><p>For now, install the web app on your laptop or add it to your iPad Home Screen.</p>{error&&<Alert variant="info">{error}</Alert>}{prompt&&<Button variant="success" className="mb-3" disabled={busy} onClick={install}>{busy?'Opening installer...':'Install Gather & Gift'}</Button>}{ipad?<><h2 className="fs-6">On your iPad or iPhone</h2><ol><li>Open this website in Safari.</li><li>Tap Share (the square with an upward arrow).</li><li>Choose Add to Home Screen. You may need to tap More or scroll to find it.</li><li>Keep Open as Web App on if shown, then tap Add.</li></ol></>:<><h2 className="fs-6">On your laptop</h2><p>In Chrome or Edge, use the install icon near the address bar, or open the browser menu and look for Install Gather &amp; Gift or Install this site as an app.</p><p>On a Mac in Safari, choose File &gt; Add to Dock.</p><h2 className="fs-6">On an iPad</h2><p>Open this website in Safari, tap Share &gt; Add to Home Screen &gt; Add. Keep Open as Web App on if shown.</p></>}<p className="small text-secondary">App Store and Microsoft Store downloads are planned for later.</p><p className="small text-secondary mb-0">An internet connection is needed to view and update your lists.</p></Modal.Body><Modal.Footer><Button variant="outline-secondary" onClick={()=>setOpen(false)}>Done</Button></Modal.Footer></Modal></>;
}

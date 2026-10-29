import {useState} from 'react';
import {Alert,Button,Card,Form} from 'react-bootstrap';
import {api} from './lib/api.js';

export default function ParentPinSettings(){
 const [pin,setPin]=useState(''),[confirmation,setConfirmation]=useState(''),[password,setPassword]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(false);
 async function save(event){
  event.preventDefault();setError('');setSaved(false);
  if(pin!==confirmation){setError('The PINs must match.');return;}
  setBusy(true);
  try{await api('/household-session/pin',{method:'POST',body:JSON.stringify({pin,password})});setPin('');setConfirmation('');setPassword('');setSaved(true);}
  catch(err){setError(err.message);}finally{setBusy(false);}
 }
 return <Card id="settings-parent-pin" tabIndex={-1} className="settings-card mb-4"><Card.Body><h2>Set / change parent PIN</h2><p>Set your PIN here before switching to child mode. It protects the return to your adult account and is shared across your children. You can save it before creating any lists.</p>{error&&<Alert variant="danger">{error}</Alert>}{saved&&<Alert variant="success">Parent PIN saved. You can now switch to an enabled child profile. Manage the child’s approved lists in Child access &amp; PIN.</Alert>}<Form onSubmit={save}><Form.Group controlId="settings-parent-pin-new" className="mb-3"><Form.Label>Parent PIN</Form.Label><Form.Control type="password" inputMode="numeric" pattern="[0-9]{6,12}" minLength={6} maxLength={12} autoComplete="new-password" required disabled={busy} value={pin} onChange={e=>setPin(e.target.value)}/><Form.Text>Choose 6 to 12 digits and keep them private.</Form.Text></Form.Group><Form.Group controlId="settings-parent-pin-confirm" className="mb-3"><Form.Label>Confirm parent PIN</Form.Label><Form.Control type="password" inputMode="numeric" autoComplete="new-password" required disabled={busy} value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></Form.Group><Form.Group controlId="settings-parent-pin-password" className="mb-3"><Form.Label>Your account password</Form.Label><Form.Control type="password" autoComplete="current-password" required disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/></Form.Group><Button type="submit" disabled={busy}>{busy?'Saving…':'Save parent PIN'}</Button></Form></Card.Body></Card>;
}

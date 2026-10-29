import { useState } from 'react';
import { Alert, Button } from 'react-bootstrap';
import { api } from './lib/api.js';
export default function FollowRequestActions({ invitationId, onChanged }) {
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const respond=async accept=>{setBusy(true);setError('');try{await api(accept?'/invitations/accept':'/invitations/'+invitationId+'/decline',{method:'POST',body:JSON.stringify(accept?{invitation_id:invitationId}:{})});await onChanged?.();window.dispatchEvent(new Event('notifications-updated'));window.dispatchEvent(new Event('invitations-updated'));}catch(err){setError(err.message);}finally{setBusy(false);}};
 return <div className="mt-2">{error && <Alert variant="danger" className="small">{error}</Alert>}<div className="d-flex gap-2"><Button size="sm" disabled={busy} onClick={()=>respond(true)}>Accept</Button><Button size="sm" variant="outline-secondary" disabled={busy} onClick={()=>respond(false)}>Decline</Button></div></div>;
}

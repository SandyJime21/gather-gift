import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, Card, Form, Modal } from 'react-bootstrap';
import { api, mediaUrl } from './lib/api.js';

export default function FamilyInvites({ households = [] }) {
  const homes = households.filter(h => ['owner', 'admin'].includes(h.role) && h.registry_type !== 'company');
  const [home, setHome] = useState('');
  const [email, setEmail] = useState(new URLSearchParams(window.location.search).get('invite_email') || '');
  const [requestOpen,setRequestOpen]=useState(Boolean(new URLSearchParams(window.location.search).get('invite_email')));
  const [connections, setConnections] = useState(null);
  const [selected, setSelected] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [checked, setChecked] = useState([]);
  const [shareHome, setShareHome] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function load() {
    setBusy(true); setError('');
    try { setConnections((await api('/family-connections')).connections); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  async function chooseHome(value) { setShareHome(value); setError(''); }
  async function share(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await api('/family-connections/' + selected + '/share', { method: 'POST', body: JSON.stringify({ household_id: Number(shareHome), share_all_profiles: true }) });
      setMessage(result.message); setSelected(null);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <Card className="settings-card mb-4"><Card.Body><h2>Family requests</h2>
    <Button onClick={()=>setRequestOpen(true)}>Send request</Button><Modal show={requestOpen} onHide={()=>setRequestOpen(false)} centered><Modal.Header closeButton><Modal.Title>Send request</Modal.Title></Modal.Header><Modal.Body><InviteRequestComposer homes={homes}/></Modal.Body></Modal>
    <InvitationInbox pendingOnly />
    <Button variant="link" className="px-0 mt-2" onClick={load} disabled={busy}>View family connections</Button>
    {error && <Alert variant="danger">{error}</Alert>}{message && <Alert variant="success">{message}</Alert>}
    {connections && <div>{connections.length === 0 && <p>No connections yet. Your first accepted invitation will appear here.</p>}{connections.map(person => <div key={person.user_id} className="border-top py-3"><strong>{person.name}</strong> <span className="small text-secondary">{person.mutual ? 'Following each other' : 'Following'}</span><div>{person.shared_households.map(h => <Link className="me-3" key={h.id} to={'/households/' + h.id}>{h.name}</Link>)}{!person.shared_households.length && <span className="small text-secondary">They have not shared a family registry yet.</span>}</div>{homes.length > 0 && <Button size="sm" variant="outline-success" className="mt-2" onClick={() => { setSelected(person.user_id); setShareHome(''); setProfiles([]); setChecked([]); }}>Share my lists back</Button>}{selected === person.user_id && <Form onSubmit={share} className="mt-3"><Form.Select aria-label="Family to share back" value={shareHome} onChange={e => chooseHome(e.target.value)} disabled={busy}><option value="">Choose your family</option>{homes.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}</Form.Select><p className="small mt-2">Shares all non-private family wishlists.</p><Button type="submit" disabled={busy || !shareHome} variant="success" size="sm">Share family wishlists</Button></Form>}</div>)}</div>}
  </Card.Body></Card>;
}


export function InviteRequestComposer({ homes }) {
  const [email,setEmail]=useState(new URLSearchParams(window.location.search).get('invite_email') || '');
  const [match,setMatch]=useState(undefined),[matches,setMatches]=useState([]),[searched,setSearched]=useState(false);
  const home=homes[0]?.id;
  const [publicGifts,setPublicGifts]=useState(null),[previewBusy,setPreviewBusy]=useState(false);
  async function viewPublic(person){setMatch(person);setMatches([]);setPublicGifts(null);if(!person?.user_id)return;setPreviewBusy(true);try{setPublicGifts((await api('/families/'+person.user_id+'/public-wishes')).wishes);}catch(err){setError(err.message);}finally{setPreviewBusy(false);}}

  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');

  async function lookup(e) {e.preventDefault();setBusy(true);setError('');setNotice('');setMatches([]);setMatch(undefined);setSearched(false);try{if(email.includes('@')){await viewPublic((await api('/families/lookup',{method:'POST',body:JSON.stringify({email:email.trim()})})).match);}else{setMatches((await api('/families/name-search',{method:'POST',body:JSON.stringify({query:email.trim()})})).matches);setSearched(true);}}catch(err){setError(err.message);}finally{setBusy(false);}}


  async function send(e) {e.preventDefault();setBusy(true);setError('');try {const result=await api('/households/'+(home || homes[0]?.id)+'/invitations',{method:'POST',body:JSON.stringify({...(match?.user_id?{recipient_user_id:match.user_id}:{email:email.trim()}),role:'shopper',share_all_profiles:true})});const delivered=result.email_message?.delivery === 'sent';if(match || delivered){setNotice('Request sent.');setEmail('');}else{setNotice('');setError('Invitation email could not be sent. Please try again later.');}setMatch(undefined);setSearched(false);setMatches([]);window.dispatchEvent(new Event('invitations-updated'));}catch(err){setError(err.message);}finally{setBusy(false);} }
  return <>{error && <Alert variant="danger">{error}</Alert>}{notice && <Alert variant="success">{notice}</Alert>}<Form onSubmit={lookup}><Form.Group controlId="quick-invite-email"><Form.Label>Adult name or email</Form.Label><Form.Control required type="search" value={email} placeholder="First name, last name or email" onChange={e=>{setEmail(e.target.value);setMatch(undefined);setMatches([]);setSearched(false);}}/></Form.Group><Button type="submit" variant="outline-success" className="mt-2" disabled={busy}>Find family</Button></Form>{matches.length>0 && <div className="d-flex flex-column gap-2 mt-3">{matches.map(person=><Button key={person.user_id+person.name} variant="light" className="text-start" onClick={()=>viewPublic(person)}>{person.photo && <img src={mediaUrl(person.photo)} alt="" style={{width:40,height:40,borderRadius:"50%",objectFit:"cover",marginRight:12}}/>}{person.name}</Button>)}</div>}{searched && !matches.length && match===undefined && <p className="small mt-2">No adult found. Try another name or their email.</p>}{match !== undefined && <div className="mt-3">{match ? <div className="d-flex align-items-center gap-3 mb-3">{match.photo && <img src={mediaUrl(match.photo)} alt="Family photo" style={{width:64,height:64,objectFit:'cover',borderRadius:'50%'}}/>}<strong>{match.name}</strong><span>Already on Gather &amp; Gift</span></div> : <Alert variant="info">No account found. We will email an invitation to sign up and connect.</Alert>}{match && <section className="my-3"><h3 className="fs-6">Public gifts</h3>{previewBusy?<p className="small">Loading...</p>:publicGifts?.length?<div className="gift-rail">{publicGifts.map(g=><Card className="gift-card" key={g.id}><Card.Body>{g.image && <img src={mediaUrl(g.image)} alt="" className="wishlist-gift-image"/>}<h3 className="item-title" title={g.name}>{g.name}</h3><small>{g.occasion || 'Everyday'}</small></Card.Body></Card>)}</div>:<p className="small text-secondary">No public gifts. Follow to see shared wishes after approval.</p>}</section>}{homes.length ? <Form onSubmit={send}><Button type="submit" className="mt-2" disabled={busy || !(home || homes[0]?.id)}>{busy ? 'Sending...' : match ? 'Send follow request' : 'Send invitation email'}</Button></Form> : <p>Create your family registry first to send an invitation.</p>}</div>}</>;
}

export function InvitationInbox({ pendingOnly = false }) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=async()=>{try{const result=await api('/invitations');setData(pendingOnly ? {...result, sent:result.sent.filter(row=>row.status==='pending'), received:result.received.filter(row=>row.status==='pending')} : result);}catch(err){setError(err.message);}};
  useEffect(()=>{const refresh=()=>{if(document.visibilityState!=='hidden')load();};refresh();const timer=setInterval(refresh,15000);window.addEventListener('invitations-updated',refresh);window.addEventListener('notifications-updated',refresh);window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);return()=>{clearInterval(timer);window.removeEventListener('invitations-updated',refresh);window.removeEventListener('notifications-updated',refresh);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);};},[]);
  const accept=async id=>{setBusy(true);setError('');try{await api('/invitations/accept',{method:'POST',body:JSON.stringify({invitation_id:id})});await load();window.dispatchEvent(new Event('notifications-updated'));window.dispatchEvent(new Event('focus'));}catch(err){setError(err.message);}finally{setBusy(false);}};
  const decline=async id=>{setBusy(true);setError('');try{await api('/invitations/'+id+'/decline',{method:'POST',body:JSON.stringify({})});await load();window.dispatchEvent(new Event('notifications-updated'));}catch(err){setError(err.message);}finally{setBusy(false);}};
  return <section className="mt-4" aria-label="Family requests"><h3>Requests</h3>{error && <Alert variant="danger">{error}</Alert>}{!data && !error && <p className="small">Loading requests...</p>}{data && <div className="request-lists">{['received','sent'].map(direction=><section key={direction} className="request-list"><h4 className="fs-6">{direction==='sent'?'Sent requests':'Received requests'} <span className="text-secondary">({data[direction].length})</span></h4>{!data[direction].length && <p className="small text-secondary">{direction==='sent'?'No requests sent yet.':'No received requests.'}</p>}{data[direction].map(row=><div key={row.id} className="border-top py-3"><strong>{direction==='sent'?(row.recipient_name || 'Request sent'):row.family}</strong><p className="small text-secondary mb-1">{direction==='sent'?'Sharing '+row.family:'Follow request'}</p><span className={'request-status request-status-'+row.status}>{row.status==='pending'?'Pending - waiting for a response':row.status==='accepted'?'Accepted':row.status==='declined'?'Declined':'Expired'}</span>{direction==='received' && row.status==='pending' && <div className="d-flex gap-2 mt-2"><Button size="sm" disabled={busy} onClick={()=>accept(row.id)}>Accept follow request</Button><Button variant="outline-secondary" size="sm" disabled={busy} onClick={()=>decline(row.id)}>Decline</Button></div>}</div>)}</section>)}</div>}</section>;
}

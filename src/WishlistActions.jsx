import {useState} from 'react';
import {Alert,Button,Form,Modal} from 'react-bootstrap';
import InlineListName from './InlineListName.jsx';
import {api} from './lib/api.js';

export default function WishlistActions({list,onRenamed,onDeleted,onSharingChanged}){
 const [confirm,setConfirm]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function share(value){
  if(busy)return;setBusy(true);setError('');
  try{await api('/wishlists/'+list.id,{method:'PATCH',body:JSON.stringify({share_publicly:value})});onSharingChanged(value);window.dispatchEvent(new Event('wishlist-updated'));window.dispatchEvent(new Event('notifications-updated'));}
  catch(err){setError(err.message);}finally{setBusy(false);}
 }
 async function remove(){
  if(busy)return;setBusy(true);setError('');
  try{await api('/wishlists/'+list.id,{method:'DELETE'});setConfirm(false);await onDeleted(list.id);window.dispatchEvent(new Event('wishlist-updated'));window.dispatchEvent(new Event('notifications-updated'));}
  catch(err){setError(err.message);}finally{setBusy(false);}
 }
 return <><div className="wishlist-inline-actions"><InlineListName key={list.id} list={list} onSaved={onRenamed}/><Button type="button" size="sm" variant="outline-danger" disabled={busy} onClick={()=>{setError('');setConfirm(true);}} aria-label={'Delete '+list.title}>Delete list</Button></div>{onSharingChanged&&<div className="mb-3"><Form.Check type="switch" role="switch" id={'inline-list-sharing-'+list.id} label="Share this list with approved followers" checked={Boolean(list.share_publicly)} disabled={busy} onChange={e=>share(e.target.checked)}/><small className="text-secondary">{list.share_publicly?'Public: approved followers can see this list when it has gifts.':'Private: this list stays within your family.'}</small>{error&&!confirm&&<Alert variant="danger" className="mt-2">{error}</Alert>}</div>}<Modal show={confirm} onHide={()=>!busy&&setConfirm(false)} centered><Modal.Header closeButton={!busy}><Modal.Title>Delete this list?</Modal.Title></Modal.Header><Modal.Body>{error&&<Alert variant="danger">{error}</Alert>}<p>Delete <strong>{list.title}</strong>?</p><p>Gifts only on this list will be deleted. Gifts on other lists will stay. Any letter linked to this list will be removed. This cannot be undone.</p></Modal.Body><Modal.Footer><Button variant="danger" disabled={busy} onClick={remove}>{busy?'Deleting...':'Yes, delete list'}</Button><Button autoFocus variant="secondary" disabled={busy} onClick={()=>setConfirm(false)}>Cancel</Button></Modal.Footer></Modal></>;
}

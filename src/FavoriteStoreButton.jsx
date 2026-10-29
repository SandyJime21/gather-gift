import {useId,useState} from 'react';
import {Button,Form} from 'react-bootstrap';
import {api} from './lib/api.js';

export default function FavoriteStoreButton({store,profile,profiles=[],onSaved}){
 const id=useId(),[open,setOpen]=useState(false),[selected,setSelected]=useState(''),[saved,setSaved]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const managed=profiles.filter((p,index,rows)=>p.can_edit&&rows.findIndex(row=>row.id===p.id)===index);
 const target=profile||managed.find(p=>String(p.id)===selected);
 const favorites=target?.favorite_stores||target?.preferences?.favorite_stores||[];
 const added=Boolean(target&&(saved.includes(target.id)||favorites.some(value=>value.toLowerCase()===store.toLowerCase())));
 if(profile?!profile.can_edit:!managed.length)return null;
 async function save(){if(!target)return;setBusy(true);setError('');try{await api('/profiles/'+target.id+'/favorite-stores',{method:'POST',body:JSON.stringify({store})});setSaved(ids=>[...ids,target.id]);setOpen(false);window.dispatchEvent(new Event('wishlist-updated'));window.dispatchEvent(new Event('notifications-updated'));await onSaved?.();}catch(err){setError(err.message);}finally{setBusy(false);}}
 return <div className="store-favorite-action"><Button type="button" size="sm" variant="link" disabled={busy||added} aria-label={profile?'Add '+store+' to '+profile.display_name+"'s favorite stores":'Add '+store+' to favorite stores'} onClick={()=>profile?save():setOpen(!open)}>{added?'✓ Favorite store':'☆ Add to favorite stores'}</Button>{open&&!profile&&<div><Form.Group controlId={id}><Form.Label>Favorite store for</Form.Label><Form.Select value={selected} disabled={busy} onChange={e=>setSelected(e.target.value)}><option value="">Choose a person or pet</option>{managed.map(p=><option key={p.id} value={p.id}>{p.display_name}{p.household_name?' / '+p.household_name:''}</option>)}</Form.Select></Form.Group><Button type="button" size="sm" className="mt-2" disabled={busy||!target||added} onClick={save}>Save favorite store</Button></div>}{error&&<p role="alert" className="small">{error}</p>}</div>;
}

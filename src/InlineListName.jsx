import {useRef,useState} from 'react';
import {Button,Form} from 'react-bootstrap';
import {api} from './lib/api.js';
export default function InlineListName({list,onSaved}){
 const [editing,setEditing]=useState(false),[title,setTitle]=useState(list.title),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const locked=useRef(false);
 const cancel=()=>{if(locked.current)return;setTitle(list.title);setError('');setEditing(false);};
 async function save(e){e.preventDefault();if(locked.current)return;const next=title.trim();if(!next){setError('Enter a list name.');return;}if(next===list.title){cancel();return;}locked.current=true;setBusy(true);setError('');try{await api('/wishlists/'+list.id,{method:'PATCH',body:JSON.stringify({title:next})});onSaved(next);setEditing(false);window.dispatchEvent(new Event('wishlist-updated'));}catch(e){setError(e.message);}finally{locked.current=false;setBusy(false);}}
 return editing?<Form className="my-2" onSubmit={save}><Form.Group controlId={'inline-list-name-'+list.id}><Form.Label className="visually-hidden">List name</Form.Label><Form.Control autoFocus required maxLength={160} value={title} disabled={busy} onChange={e=>{setTitle(e.target.value);setError('');}} onKeyDown={e=>{if(e.key==='Escape'){e.preventDefault();cancel();}}}/></Form.Group><div className="d-flex gap-2 mt-2"><Button size="sm" type="submit" disabled={busy||!title.trim()}>{busy?'Saving...':'Save'}</Button><Button size="sm" type="button" variant="link" disabled={busy} onClick={cancel}>Cancel</Button></div>{error&&<p role="alert" className="small text-danger mb-0">{error}</p>}</Form>:<Button type="button" variant="link" className="p-0 text-start" title="Click to rename list" aria-label={'Rename '+list.title} onClick={()=>{setTitle(list.title);setEditing(true);}}>{list.title}</Button>;
}

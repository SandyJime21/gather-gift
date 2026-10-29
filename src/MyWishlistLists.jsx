import {useEffect,useState} from 'react';
import {Alert,Form} from 'react-bootstrap';
import {Link} from 'react-router-dom';
import {api} from './lib/api.js';
import WishlistActions from './WishlistActions.jsx';

export default function MyWishlistLists({profiles=[]}){
 const managed=profiles.filter((p,i,rows)=>p.can_edit&&rows.findIndex(row=>row.id===p.id)===i);
 const [person,setPerson]=useState(''),[lists,setLists]=useState([]),[error,setError]=useState(''),[loading,setLoading]=useState(false),[revision,setRevision]=useState(0);
 const selected=managed.some(p=>String(p.id)===person)?person:String(managed[0]?.id||'');
 useEffect(()=>{const refresh=()=>setRevision(v=>v+1);window.addEventListener('wishlist-updated',refresh);return()=>window.removeEventListener('wishlist-updated',refresh);},[]);
 useEffect(()=>{let active=true;setLists([]);setError('');if(!selected)return;setLoading(true);api('/profiles/'+selected+'/wishlists').then(result=>{if(active)setLists(result.wishlists||[]);}).catch(err=>{if(active)setError(err.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[selected,revision]);
 if(!managed.length)return null;
 return <section className="my-wishlist-lists mb-4"><h2>My lists</h2>{managed.length>1&&<Form.Group controlId="my-lists-member" className="mb-3"><Form.Label>Whose lists?</Form.Label><Form.Select value={selected} onChange={e=>setPerson(e.target.value)}>{managed.map(p=><option value={p.id} key={p.id}>{p.display_name}</option>)}</Form.Select></Form.Group>}{error&&<Alert variant="danger">{error}</Alert>}{loading?<p role="status">Loading lists...</p>:lists.length?lists.map(list=><div className="my-wishlist-list-row" key={list.id}><WishlistActions onSharingChanged={shared=>setLists(rows=>rows.map(row=>row.id===list.id?{...row,share_publicly:shared}:row))} list={list} onRenamed={title=>setLists(rows=>rows.map(row=>row.id===list.id?{...row,title}:row))} onDeleted={id=>setLists(rows=>rows.filter(row=>row.id!==id))}/><Link to={'/profiles/'+selected+'?wishlist='+list.id}>Open wishes</Link></div>):<p>No lists yet. Choose New list to create one.</p>}</section>;
}

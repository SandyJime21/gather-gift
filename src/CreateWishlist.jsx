import ListTransfer from './ListTransfer.jsx';
import {useEffect,useId,useState} from 'react';
import {Link} from 'react-router-dom';
import {Alert,Button,Form,Modal,Nav} from 'react-bootstrap';
import {api} from './lib/api.js';
import {ListDelivery} from './ListDelivery.jsx';

export default function CreateWishlist({profiles=[]}){
 const managed=profiles.filter((profile,index,rows)=>profile.can_edit&&rows.findIndex(row=>row.id===profile.id)===index);
 const [open,setOpen]=useState(false),[context,setContext]=useState('new'),[mode,setMode]=useState('create');
 const [person,setPerson]=useState(''),[lists,setLists]=useState([]),[listId,setListId]=useState(''),[title,setTitle]=useState('');
 const [catalog,setCatalog]=useState([]),[sourceId,setSourceId]=useState(''),[family,setFamily]=useState('');
 const [selected,setSelected]=useState([]),[allowChildItems,setAllowChildItems]=useState(true),[created,setCreated]=useState([]);
 const [busy,setBusy]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const [deleteTarget,setDeleteTarget]=useState(null);
 const formId=useId();
 const managedHomes=new Set(managed.map(p=>String(p.household_id||p.household_name||'family')));
 const readable=profiles.filter((p,i,all)=>managedHomes.has(String(p.household_id||p.household_name||'family'))&&all.findIndex(q=>q.id===p.id)===i);
 const profileKey=readable.map(row=>row.id).join(',');
 const familyKey=p=>String(p.household_id||p.household_name||'family');
 const listKey=row=>familyKey(row.profile)+':'+row.title.trim().toLocaleLowerCase();
 const groupLists=rows=>{const groups=new Map();for(const row of rows)if(!groups.has(listKey(row)))groups.set(listKey(row),row);return [...groups.values()];};
 useEffect(()=>{
  if(!open||mode!=='edit'||!person)return;
  let active=true;setLists([]);setListId('');setTitle('');setLoading(true);
  api('/profiles/'+person+'/wishlists').then(data=>{if(active){setLists(data.wishlists||[]);setListId(String(data.wishlists?.[0]?.id||''));setTitle(data.wishlists?.[0]?.title||'');}}).catch(err=>{if(active)setError(err.message);}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[open,mode,person]);
 useEffect(()=>{
  if(!open||mode!=='assign')return;
  let active=true;setCatalog([]);setLoading(true);
  Promise.all(readable.map(async profile=>({profile,lists:(await api('/profiles/'+profile.id+'/wishlists')).wishlists||[]}))).then(groups=>{
   if(!active)return;
   const options=groups.flatMap(group=>group.lists.map(list=>({...list,profile:group.profile})));
   setCatalog(options);setSourceId(current=>{const old=options.find(row=>String(row.id)===current);return String((old?groupLists(options).find(row=>listKey(row)===listKey(old)):groupLists(options)[0])?.id||'');});
  }).catch(err=>{if(active)setError(err.message);}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[open,mode,profileKey]);
 const grouped=groupLists(catalog);
 const source=catalog.find(row=>String(row.id)===sourceId);
 const sameName=(a,b)=>a.trim().toLocaleLowerCase()===b.trim().toLocaleLowerCase();
 const alreadyHas=profile=>mode==='assign'&&source&&catalog.some(row=>row.profile.id===profile.id&&sameName(row.title,source.title));
 const targets=(mode==='assign'?readable:managed).filter(profile=>(!family||familyKey(profile)===family)&&(mode!=='assign'||!source||familyKey(profile)===familyKey(source.profile)));
 const eligible=targets.filter(profile=>profile.can_edit&&!alreadyHas(profile));
 function changeMode(next){setLoading(false);setMode(next);setSelected([]);setCreated([]);setMessage('');setError('');setFamily('');if(next==='create')setTitle('');if(next==='assign'&&mode==='edit'&&listId)setSourceId(listId);}
 function start(manage){setLoading(false);setSourceId('');setListId('');setCatalog([]);setContext(manage?'manage':'new');setOpen(true);setMode(manage?'edit':'create');setPerson(String(managed[0]?.id||''));setTitle('');setSelected([]);setCreated([]);setMessage('');setError('');setFamily('');setAllowChildItems(true);}
 async function save(event){
  event.preventDefault();setBusy(true);setError('');setMessage('');
  try{
   const body=mode==='edit'?{title}:mode==='assign'?{source_wishlist_id:Number(sourceId),profile_ids:selected,allow_child_items:allowChildItems}:{title,profile_ids:selected,allow_child_items:allowChildItems};
   const result=await api(mode==='edit'?'/wishlists/'+listId:'/wishlists/batch',{method:mode==='edit'?'PATCH':'POST',body:JSON.stringify(body)});
   if(mode==='edit'){setLists(rows=>rows.map(row=>String(row.id)===listId?{...row,title}:row));setMessage('List name saved.');}
   else{setCreated(result.wishlists||[]);setMessage(mode==='assign'?'Assigned. Each member has a separate list with this name. Existing lists and gifts were kept.':'Lists created. Each person has their own list for wishes.');setSelected([]);if(mode==='create')setTitle('');}
   window.dispatchEvent(new Event('wishlist-updated'));
   if(mode==='assign'){
    const options=await Promise.all(readable.map(async profile=>({profile,lists:(await api('/profiles/'+profile.id+'/wishlists')).wishlists||[]})));
    setCatalog(options.flatMap(group=>group.lists.map(list=>({...list,profile:group.profile}))));
   }
  }catch(err){setError(err.message);}finally{setBusy(false);}
 }
 async function assignMember(profile){
  if(busy||loading||!source||!profile.can_edit||alreadyHas(profile))return;
  setBusy(true);setSelected([profile.id]);setError('');setMessage('Assigning '+source.title+' to '+profile.display_name+'...');
  try{
   const result=await api('/wishlists/batch',{method:'POST',body:JSON.stringify({source_wishlist_id:Number(sourceId),profile_ids:[profile.id],allow_child_items:allowChildItems})});
   setCatalog(rows=>{const next=[...rows];for(const list of result.wishlists||[])if(!next.some(row=>row.id===list.id))next.push({...list,profile});return next;});
   setMessage(source.title+' assigned to '+profile.display_name+'.');
   window.dispatchEvent(new Event('wishlist-updated'));
  }catch(err){setMessage('');setError(err.message);}finally{setSelected([]);setBusy(false);}
 }
 async function removeList(){
  if(!deleteTarget)return;setBusy(true);setError('');
  try{await api('/wishlists/'+deleteTarget.id,{method:'DELETE'});const remaining=lists.filter(row=>row.id!==deleteTarget.id);setLists(remaining);setListId(String(remaining[0]?.id||''));setTitle(remaining[0]?.title||'');setCatalog(rows=>rows.filter(row=>row.id!==deleteTarget.id));setCreated(rows=>rows.filter(row=>row.id!==deleteTarget.id));setDeleteTarget(null);setMessage('List deleted. Gifts on other lists were kept.');window.dispatchEvent(new Event('wishlist-updated'));window.dispatchEvent(new Event('notifications-updated'));}
  catch(err){setError(err.message);setDeleteTarget(null);}finally{setBusy(false);}
 }
 const families=[...new Map(managed.map(profile=>[String(profile.household_id||profile.household_name),profile.household_name||'My family'])).entries()];
 return <><Button type="button" variant="outline-success" title="Create a named wishlist for one or several members." onClick={e=>{e.preventDefault();e.stopPropagation();start(false);}}>New list</Button><Button variant="outline-success" type="button" title="Edit lists or create matching lists for other members." onClick={e=>{e.preventDefault();e.stopPropagation();start(true);}}>Manage lists</Button>
 <Modal show={open} onClick={e=>e.stopPropagation()} enforceFocus={!deleteTarget} onHide={()=>{if(!busy)setOpen(false);}} centered scrollable><Modal.Header closeButton={!busy}><Modal.Title>{context==='manage'?'Manage lists':'Add a list'}</Modal.Title></Modal.Header><Modal.Body>
 <Nav variant="pills" className="mb-3" activeKey={mode}><Nav.Link as="button" type="button" disabled={busy} active={mode===(context==='manage'?'edit':'create')} onClick={()=>changeMode(context==='manage'?'edit':'create')}>{context==='manage'?'Edit lists':'Create new'}</Nav.Link><Nav.Link as="button" type="button" disabled={busy} active={mode==='assign'} onClick={()=>changeMode('assign')}>Assign existing</Nav.Link></Nav>
 {error&&<Alert variant="danger">{error}</Alert>}{message&&<Alert variant="success">{message}</Alert>}{loading&&<p role="status">Loading lists…</p>}
 <Form id={formId} onClick={e=>e.stopPropagation()} onSubmit={e=>{e.preventDefault();e.stopPropagation();if(mode!=='assign')save(e);}}>
 {mode==='edit'?<><Form.Group controlId={formId+'-person'} className="mb-3"><Form.Label>For</Form.Label><Form.Select value={person} disabled={busy} onChange={e=>setPerson(e.target.value)}><option value="">Choose a member</option>{managed.map(profile=><option key={profile.id} value={profile.id}>{profile.display_name} / {profile.household_name}</option>)}</Form.Select></Form.Group><Form.Group controlId={formId+'-list'} className="mb-3"><Form.Label>List</Form.Label><Form.Select value={listId} required disabled={busy||loading} onChange={e=>{setListId(e.target.value);setTitle(lists.find(row=>String(row.id)===e.target.value)?.title||'');}}><option value="">Choose a list</option>{lists.map(list=><option key={list.id} value={list.id}>{list.title}</option>)}</Form.Select></Form.Group>{!loading&&!lists.length&&<p>No lists yet. Use New list to create one.</p>}{listId&&<div className="d-flex flex-wrap gap-2 mb-3"><Button as={Link} to={'/profiles/'+person+'?wishlist='+listId} onClick={()=>setOpen(false)}>Open list to edit wishes</Button><Button type="button" variant="outline-success" disabled={busy} onClick={()=>{setSourceId(listId);changeMode('assign');}}>Assign this list to other members</Button><Button type="button" variant="outline-danger" disabled={busy} onClick={()=>setDeleteTarget({id:Number(listId),title:lists.find(row=>String(row.id)===listId)?.title||title,name:managed.find(row=>String(row.id)===person)?.display_name})}>Delete list</Button></div>}</>:<>
 {mode==='assign'&&<><Form.Group controlId={formId+'-source'} className="mb-3"><Form.Label>Existing list</Form.Label><Form.Select required disabled={busy||loading} value={sourceId} onChange={e=>{setSourceId(e.target.value);setSelected([]);setCreated([]);setMessage('');}}><option value="">Choose a list</option>{grouped.filter(row=>!family||familyKey(row.profile)===family).map(list=><option key={list.id} value={list.id}>{list.title}{families.length>1?' / '+list.profile.household_name:''}</option>)}</Form.Select></Form.Group><p className="small text-secondary">Reuse the name only. Each person missing it gets their own empty, private list. Gifts are not copied or combined.</p>{!loading&&!catalog.length&&<p>Create a list first, then assign its name to other members.</p>}</>}
 {families.length>1&&<Form.Group controlId={formId+'-family'} className="mb-3"><Form.Label>Family</Form.Label><Form.Select value={family} disabled={busy} onChange={e=>{setFamily(e.target.value);setSelected([]);if(mode==='assign')setSourceId(String(grouped.find(row=>!e.target.value||familyKey(row.profile)===e.target.value)?.id||''));}}><option value="">All families I manage</option>{families.map(([id,name])=><option key={id} value={id}>{name}</option>)}</Form.Select></Form.Group>}
 <fieldset className="mb-3" disabled={busy||loading||(mode==='assign'&&!source)}><legend className="fs-6">{mode==='assign'?'Family members':'Who needs this list?'}</legend>{mode==='assign'?<p className="small">Here are your family lists. Checked means assigned. Check an unassigned member to add this list immediately. Existing lists and gifts stay safe.</p>:<Button type="button" size="sm" variant="link" className="p-0 mb-2" onClick={()=>setSelected(eligible.map(profile=>profile.id))}>Select all managed members</Button>}{targets.map(profile=><div key={profile.id}><Form.Check id={formId+'-target-'+profile.id} label={profile.display_name+' / '+profile.household_name} checked={Boolean(alreadyHas(profile))||selected.includes(profile.id)} disabled={Boolean(alreadyHas(profile))||(mode==='assign'&&!profile.can_edit)} onChange={e=>{e.stopPropagation();if(mode==='assign'){if(e.target.checked)assignMember(profile);}else setSelected(ids=>e.target.checked?[...ids,profile.id]:ids.filter(id=>id!==profile.id));}}/>{alreadyHas(profile)&&<small className="text-secondary">Assigned</small>}{mode==='assign'&&!profile.can_edit&&!alreadyHas(profile)&&<small className="text-secondary">This adult assigns their own lists.</small>}</div>)} <p className="small text-secondary mt-2">Adults with their own login manage their own lists.</p>
 {managed.some(profile=>(mode==='assign'?targets.some(p=>p.id===profile.id):selected.includes(profile.id))&&profile.profile_type!=='pet'&&!profile.is_adult)&&<><Form.Check type="switch" id={formId+'-child'} label="Let selected children add wishes to this list in child mode" checked={allowChildItems} onChange={e=>setAllowChildItems(e.target.checked)}/><p className="small text-secondary">Approves only newly created lists. Child mode and your parent PIN must be set up separately.</p></>}</fieldset>
 </>}
 {mode!=='assign'&&<Form.Group controlId={formId+'-title'}><Form.Label>List name</Form.Label><Form.Control required disabled={busy} maxLength={160} placeholder="Birthday, Christmas…" value={title} onChange={e=>setTitle(e.target.value)}/></Form.Group>}
 </Form>
 {mode==='edit'&&listId&&<ListDelivery listId={listId}/>}
 {mode!=='assign'&&created.length>0&&<div className="mt-3">{created.map(list=><Link key={list.id} className="d-block" to={'/profiles/'+list.profile_id+'?wishlist='+list.id} onClick={()=>setOpen(false)}>{list.name}: {list.title}</Link>)}{mode==='create'&&<Button type="button" variant="link" className="px-0 mt-2" onClick={()=>{setSourceId(String(created[0].id));changeMode('assign');}}>Assign this list to more members</Button>}</div>}
 </Modal.Body><Modal.Footer>{mode==='assign'?<Button type="button" variant="secondary" disabled={busy} onClick={e=>{e.preventDefault();e.stopPropagation();setOpen(false);}}>Done</Button>:<Button type="submit" form={formId} disabled={busy||loading||(mode==='edit'?!listId:!selected.length)||(mode==='assign'&&!sourceId)}>{mode==='edit'?'Save list name':mode==='assign'?'Assign selected members':'Create list'}</Button>}</Modal.Footer></Modal><Modal show={Boolean(deleteTarget)} onHide={()=>{if(!busy)setDeleteTarget(null);}} centered><Modal.Header closeButton={!busy}><Modal.Title as="h2">Delete this list?</Modal.Title></Modal.Header><Modal.Body><p>Delete <strong>{deleteTarget?.title}</strong> for {deleteTarget?.name}?</p><p>Gifts only on this list will be deleted. Gifts also on other lists will stay there. Any wishlist letter linked to this list will be removed.</p><p className="small text-secondary">This cannot be undone.</p>{deleteTarget&&<ListTransfer key={deleteTarget.id} list={deleteTarget} inline onBusyChange={setBusy}/>}</Modal.Body><Modal.Footer><Button type="button" variant="danger" disabled={busy} onClick={removeList}>{busy?'Deleting...':'Yes, delete list'}</Button><Button type="button" variant="outline-secondary" autoFocus disabled={busy} onClick={()=>setDeleteTarget(null)}>Cancel</Button></Modal.Footer></Modal></>;
}

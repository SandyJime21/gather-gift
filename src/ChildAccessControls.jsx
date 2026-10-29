import {useEffect,useState} from 'react';
import {Alert,Form} from 'react-bootstrap';
import {api} from './lib/api.js';

const labels={web_search:'Search online for gifts',product_links:'Add product links',manage_pets:'View and edit family pet wishes',switch_siblings:'Switch to sibling wishlists',game_invites:'See family game invitations'};
export default function ChildAccessControls({profileId}) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  useEffect(()=>{let active=true;setData(null);api('/profiles/'+profileId+'/child-controls').then(result=>{if(active)setData(result);}).catch(err=>{if(active)setError(err.message);});return()=>{active=false;};},[profileId]);
  async function change(key,value){setBusy(true);setError('');try{setData(await api('/profiles/'+profileId+'/child-controls',{method:'PATCH',body:JSON.stringify({[key]:value})}));}catch(err){setError(err.message);}finally{setBusy(false);}}
  return <details className="profile-edit-section mb-3"><summary>Child access · parent approval</summary><div className="pt-3"><p>Extra activities are off until you allow them. Adult account settings, payments, private gifts, and sharing controls stay restricted.</p>{error&&<Alert variant="danger">{error}</Alert>}{data?.available?Object.entries(labels).map(([key,label])=><Form.Check type="switch" role="switch" id={'child-access-'+profileId+'-'+key} key={key} label={label} checked={data.controls[key]} disabled={busy} onChange={event=>change(key,event.target.checked)}/>):<p className="text-secondary">Enable this child's wishlist access first to manage permissions.</p>}</div></details>;
}

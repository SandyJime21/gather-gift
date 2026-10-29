import {useEffect,useState} from 'react';
import {api,mediaUrl} from './lib/api.js';
export const defaultAvatars=[['flower','Flower','\u273f'],['paw','Paw','\ud83d\udc3e'],['star','Star','\u2b50'],['sun','Sun','\u2600'],['cat','Cat','\ud83d\udc31'],['dog','Dog','\ud83d\udc36'],['rabbit','Rabbit','\ud83d\udc30'],['bird','Bird','\ud83d\udc26'],['fish','Fish','\ud83d\udc20']];
export default function MemberAvatar({name='',photo,avatarKey='flower',className=''}){
 const source=photo || (/^a[0-9]+$/.test(avatarKey)?'/api/avatars/'+avatarKey.slice(1)+'/art':null);
 const [failed,setFailed]=useState(false);useEffect(()=>setFailed(false),[source]);
 return <span className={'member-avatar-picture '+className} aria-hidden="true">{source&&!failed?<img src={mediaUrl(source)} alt="" loading="lazy" onError={()=>setFailed(true)}/>:<span>{defaultAvatars.find(a=>a[0]===avatarKey)?.[2] || name.trim().charAt(0).toUpperCase() || '\u273f'}</span>}</span>;
}
export function AvatarPicker({value,onChange}){
 const [avatars,setAvatars]=useState([]),[error,setError]=useState('');
 useEffect(()=>{api('/avatars').then(r=>setAvatars(r.avatars||[])).catch(e=>setError(e.message));},[]);
 return <fieldset className="my-3"><legend className="fs-6">Choose a cartoon</legend>{error&&<p className="small text-secondary">More cartoons could not load.</p>}<div className="avatar-choice-grid">{[...defaultAvatars.map(([key,name])=>({key,name})),...avatars].map(a=><button type="button" key={a.key} className="avatar-choice" aria-label={a.name} aria-pressed={value===a.key} title={a.name} onClick={()=>onChange(a.key)}><MemberAvatar name={a.name} avatarKey={a.key}/></button>)}</div></fieldset>;
}

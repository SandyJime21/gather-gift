import StoreLogo from './StoreLogo.jsx';
import PreferenceEntry from './PreferenceEntry.jsx';
import {useState} from 'react';
import MemberAvatar from './MemberAvatar.jsx';
import {Button,Form,Modal,ProgressBar} from 'react-bootstrap';

const listValue=value=>(value||[]).join(', ');
const split=value=>value.split(',').map(v=>v.trim()).filter(Boolean);
const sizeValue=value=>Object.entries(value||{}).map(([k,v])=>k+': '+v).join(', ');
const sizes=value=>Object.fromEntries(value.split(',').map(v=>{const i=v.indexOf(':');return i<0?['Size',v.trim()]:[v.slice(0,i).trim(),v.slice(i+1).trim()];}).filter(([k,v])=>k&&v));
const clothingAliases={top:['top','tops','shirt','shirts'],bottom:['bottom','bottoms','pants','trousers']};
function AdultClothingSizes({profile,onChange,prefix}){
 const current=profile.clothing_sizes||{};
 return <>{Object.entries(clothingAliases).map(([key,aliases])=>{
  const entries=Object.entries(current).filter(([name])=>aliases.includes(name.toLowerCase()));
  return <Form.Group controlId={prefix+'-clothing_sizes-'+key} className="mb-3" key={key}><Form.Label>{key==='top'?'Top size':'Bottom size'}</Form.Label><Form.Control value={entries.map(([,value])=>value).join(' / ')} placeholder={key==='top'?'e.g. M':'e.g. 8 or 32?30'} maxLength={200} onChange={e=>{const next=Object.fromEntries(Object.entries(current).filter(([name])=>!aliases.includes(name.toLowerCase())));if(e.target.value.trim())next[key]=e.target.value;onChange(next);}}/></Form.Group>;
 })}{Object.keys(current).some(key=>!Object.values(clothingAliases).flat().includes(key.toLowerCase()))&&<Form.Group controlId={prefix+'-clothing_sizes-other'} className="mb-3"><Form.Label>Other clothing sizes</Form.Label><Form.Control defaultValue={sizeValue(Object.fromEntries(Object.entries(current).filter(([key])=>!Object.values(clothingAliases).flat().includes(key.toLowerCase()))))} maxLength={1000} onChange={e=>onChange({...Object.fromEntries(Object.entries(current).filter(([key])=>Object.values(clothingAliases).flat().includes(key.toLowerCase()))),...sizes(e.target.value)})}/></Form.Group>}</>;
}
export function preferencePayload(profile){return Object.fromEntries(['favorite_colors','favorite_brands','favorite_stores','favorite_snacks','favorite_characters','interests','hobbies','clothing_sizes','shoe_sizes','gift_preferences','allergies'].map(key=>[key,profile[key] ?? (['clothing_sizes','shoe_sizes'].includes(key)?{}:['gift_preferences','allergies'].includes(key)?'':[])]));}

export function ProfilePreferencesFields({profile,onChange,prefix='gift-profile'}){
 const pet=profile.profile_type==='pet',child=!pet && profile.is_adult===false;
 const change=(key,value)=>onChange({...profile,[key]:value});
 const field=([key,label])=><PreferenceEntry key={prefix+key} id={prefix+'-'+key} field={key} label={label} values={profile[key]||[]} onChange={value=>change(key,value)} placeholder={key==='interests'&&child?'Minnie Mouse, dinosaurs, painting':key==='favorite_colors'?'Pink, purple':key==='favorite_brands'?'Add the brands they love':'Separate with commas'}/>;
 const primary=pet?[['interests','Favorite activities'],['favorite_snacks','Favorite treats']]:child?[['interests','What are they into right now?'],['favorite_colors','Favorite colors'],['favorite_snacks','Favorite snacks']]:[['favorite_brands','Favorite brands'],['favorite_stores','Favorite stores'],['favorite_colors','Favorite colors'],['favorite_snacks','Favorite snacks'],['interests','Interests & hobbies']];
 const extra=pet?[['favorite_brands','Favorite brands'],['favorite_stores','Favorite stores']]:child?[['favorite_characters','Favorite characters'],['favorite_brands','Favorite brands'],['favorite_stores','Favorite stores']]:[['favorite_characters','Favorite characters']];
 return <section className="gift-profile-fields my-3"><h3 className="fs-6">{pet?'Treats, toys & care':child?'Their favorites right now':'Make gifting easy'}</h3><p className="small text-secondary">Type your own favorites or search online. Both count toward profile completion. These details are shared with people allowed to view this profile.{child?' A parent manages these details.':''}{pet?' Manage these details for your pet.':''}</p><div className="gift-profile-field-grid">{primary.map(field)}</div>{!pet && <div id={!child?prefix+'-clothing_sizes':undefined} className={'gift-profile-field-grid'+(!child?' adult-size-fields':'')}>{!child&&<AdultClothingSizes profile={profile} prefix={prefix} onChange={value=>change('clothing_sizes',value)}/>}{(child?[['clothing_sizes','Clothing sizes','Shirt: M, pants: 8'],['shoe_sizes','Shoe sizes','US: 7, EU: 38']]:[['shoe_sizes','Shoe sizes','US: 7, EU: 38']]).map(([key,label,placeholder])=><Form.Group controlId={prefix+'-'+key} className="mb-3" key={prefix+key}><Form.Label>{label}</Form.Label><Form.Control defaultValue={sizeValue(profile[key])} placeholder={placeholder} maxLength={1000} onChange={e=>change(key,sizes(e.target.value))}/></Form.Group>)}</div>}<Form.Group controlId={prefix+'-allergies'} className="mb-3"><Form.Label>Allergies & sensitivities</Form.Label><Form.Control as="textarea" rows={2} maxLength={2000} value={profile.allergies||''} placeholder="e.g. peanuts, wool; or none known" onChange={e=>change('allergies',e.target.value)}/><Form.Text>Enter &quot;None known&quot; if applicable. Leaving this blank means it has not been provided.</Form.Text></Form.Group><Form.Group controlId={prefix+'-preferences'}><Form.Label>{pet?'Favorite treats or toys':'What gifts would they love?'}</Form.Label><Form.Control as="textarea" rows={2} value={profile.gift_preferences||''} maxLength={2000} placeholder={pet?'Soft toys, crunchy treats':'Art supplies, cozy pajamas, books; anything to keep in mind'} onChange={e=>change('gift_preferences',e.target.value)}/></Form.Group><details className="mt-3"><summary>More favorites (optional)</summary><div className="gift-profile-field-grid mt-3">{extra.map(field)}</div></details></section>;
}

const filled=value=>Array.isArray(value)?value.some(filled):value&&typeof value==='object'?Object.values(value).some(filled):value!==null&&value!==undefined&&String(value).trim()!=='';
const profilePicture=profile=>profile.photo_path || (profile.avatar_key&&!['flower','paw'].includes(profile.avatar_key)?profile.avatar_key:'');
export function calculateProfileCompletion(profile){
 profile={...(profile.preferences||{}),...profile};
 const fields=[['Photo',profilePicture(profile)],['Birthday',profile.birthday],['Allergies or none known',profile.allergies],['Current favorites',[...(profile.interests||[]),...(profile.favorite_characters||[]),...(profile.hobbies||[]),...(profile.favorite_snacks||[])]]];
 if(profile.profile_type==='pet')fields.push(['Favorite treats or toys',profile.gift_preferences]);
 else{fields.push(['Clothing size',profile.clothing_sizes],['Shoe size',profile.shoe_sizes],['Favorite colors',profile.favorite_colors]);if(profile.is_adult!==false)fields.push(['Favorite brands',profile.favorite_brands],['Favorite stores',profile.favorite_stores],['Gift preferences',profile.gift_preferences]);}
 const missing=fields.filter(([,value])=>!filled(value)).map(([label])=>label),total=fields.length,completed=total-missing.length;
 return {percent:Math.round(completed*100/total),missing,total,completed};
}

export function ProfileCompletionBadge({name,progress}){
 const hint=progress.missing?.length?'Still to add: '+progress.missing.join(', '):progress.percent===100?'Profile complete':'Open profile to see missing details';
 return <span className="settings-profile-progress" tabIndex={0} title={hint} aria-label={name+' profile completion: '+progress.percent+'%. '+hint}><span>{progress.percent===100&&<span className="profile-complete-check" aria-hidden="true">✓ </span>}{progress.percent}%</span><progress max="100" value={progress.percent} aria-label={name+' profile complete'}/><small>complete</small></span>;
}

export function ProfileCompletion({profile,children,live=false}){
 const progress=live||!profile.completion||(profilePicture(profile)&&profile.completion.missing?.includes('Photo'))?calculateProfileCompletion(profile):profile.completion;
 return <section className="profile-completion my-3" aria-label={profile.display_name+' profile completion'}><div className="profile-completion-heading"><div><span className="profile-completion-eyebrow">Make gifting personal</span><strong>{profile.display_name}'s gift profile: {progress.percent}% complete</strong></div><span className="profile-completion-number" aria-hidden="true">{progress.percent}%</span></div><ProgressBar now={progress.percent} aria-label="Gift profile completion" className="my-2"/>{progress.total!=null&&<p className="small profile-completion-count">{progress.completed} of {progress.total} details added</p>}{progress.missing?.length>0?<><p className="visually-hidden">Still to add: {progress.missing.join(', ')}.</p><p className="small mb-2">{profilePicture(profile)?'Your profile picture is added. Remaining details:':'Remaining profile details:'}</p><ul className="profile-completion-checklist" aria-label="Missing profile details">{progress.missing.map(label=><li key={label}>{label}</li>)}</ul></>:<p className="small mb-2">Ready to help people choose a thoughtful gift.</p>}{children}</section>;
}

export function GiftGuide({profile={},compact=false,name=''}){
 const display=value=>Array.isArray(value)?value.join(', '):value&&typeof value==='object'?sizeValue(value):value;
 const pet=profile.profile_type==='pet';
 const quick=(pet?[['Favorite treats',profile.favorite_snacks],['Favorite activities',profile.interests]]:[['Clothing sizes',profile.clothing_sizes],['Shoe sizes',profile.shoe_sizes],['Favorite colors',profile.favorite_colors],['Favorite snacks',profile.favorite_snacks],['Favorite brands',profile.favorite_brands],['Favorite stores',profile.favorite_stores]]).map(([label,value])=>[label,display(value)]);
 const more=[...(pet?[['Favorite brands',profile.favorite_brands],['Favorite stores',profile.favorite_stores]]:[]),['Into right now',[...(pet?[]:profile.interests||[]),...(profile.favorite_characters||[]),...(profile.hobbies||[])]],['Gift ideas',profile.gift_preferences]].map(([label,value])=>[label,display(value)]).filter(([,value])=>value);
 const favorites=<dl className="gift-guide-details">{more.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
 return <section className={'gift-guide my-3'+(compact?' gift-guide-compact':'')}><h2 className={compact?'gift-guide-title':'fs-5'}>Gift guide{name?' for '+name:''}</h2><dl className="gift-guide-quick">{quick.map(([label,value])=><div key={label}><dt>{label}</dt><dd className={!value?'gift-guide-missing':undefined}>{label==='Favorite stores'&&profile.favorite_stores?.length?profile.favorite_stores.map(store=><span className="favorite-store-chip me-1" key={store}><StoreLogo name={store}/>{store}</span>):value || 'Not added yet'}</dd></div>)}</dl><div className="gift-guide-allergies"><strong>Allergies & sensitivities: </strong>{profile.allergies?.trim() || 'Not provided. Ask before choosing food or sensitive materials.'}</div>{compact?<details><summary>More favorites & gift ideas</summary>{favorites}</details>:favorites}{!more.length&&!quick.some(([,value])=>value)&&<p className="small mb-0">More favorites and sizes can be added to this profile.</p>}</section>;
}

export function DiscoverGiftProfile({profile,children}){
 const pet=profile.profile_type==='pet',preferences=profile.preferences||profile;
 return <article className="discover-gift-profile"><header><MemberAvatar name={profile.display_name} photo={profile.photo_path} avatarKey={pet?'paw':profile.avatar_key}/><div><h3>{profile.display_name}{profile.is_me?' (you)':''}</h3><p>{pet?'Treats, toys and little favorites':profile.is_me?'Help your people find gifts you love':'Favorites managed by their family'}</p></div></header><div className="discover-favorite-grid">{(pet?[['Favorite treats',preferences.favorite_snacks],['Favorite toys',preferences.gift_preferences]]:[['Favorite brands',preferences.favorite_brands],['Favorite stores',preferences.favorite_stores],['Favorite colors',preferences.favorite_colors],['Into right now',[...(preferences.interests||[]),...(preferences.favorite_characters||[]),...(preferences.hobbies||[])]]]).map(([label,value])=><div key={label}><strong>{label}</strong><span>{Array.isArray(value)?value.join(', ')||'Add your favorites':value||'Add your favorites'}</span></div>)}</div><div className="discover-profile-action">{children}</div></article>;
}

export function GiftGuideButton({profile,name=''}){
 const [open,setOpen]=useState(false);
 const title=(name || 'Recipient')+"'s gift guide";
 return <><div className="gift-guide-action"><Button type="button" variant="light" size="sm" className="gift-guide-help" aria-label={title} title={title} onClick={()=>setOpen(true)}>?</Button></div><Modal show={open} onHide={()=>setOpen(false)} centered><Modal.Header closeButton><Modal.Title>{title}</Modal.Title></Modal.Header><Modal.Body><GiftGuide profile={profile} name={name}/></Modal.Body></Modal></>;
}

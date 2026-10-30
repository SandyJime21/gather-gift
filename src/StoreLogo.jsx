import {useState} from 'react';
import {findStore,storeLogo} from './lib/storeCatalog.js';
export default function StoreLogo({name}){
 const [failed,setFailed]=useState(false),store=findStore(name);
 return store&&!failed?<img className="store-logo" src={storeLogo(store)} alt="" loading="lazy" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>:<span className="store-logo store-logo-initial" aria-hidden="true">{name?.[0]||'S'}</span>;
}

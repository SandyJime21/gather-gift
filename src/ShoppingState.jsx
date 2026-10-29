import {createContext,useContext,useEffect,useRef,useState} from 'react';
import {api} from './lib/api.js';
const ShoppingContext=createContext(null);
export const useShoppingState=()=>useContext(ShoppingContext);
export function ShoppingProvider({user,children}){
 const [rows,setRows]=useState([]),[items,setItems]=useState({}),[loaded,setLoaded]=useState(false);
 const sequence=useRef(0);
 const enabled=Boolean(user&&!user.is_child&&!user.is_support);
 const refresh=async()=>{if(!enabled)return;const seq=++sequence.current;const data=await api('/my-shopping');if(seq!==sequence.current)return;const next=data.reservations||[];setRows(next);setItems(Object.fromEntries(next.map(r=>[r.item.id,r.item])));setLoaded(true);};
 useEffect(()=>{setRows([]);setItems({});setLoaded(false);if(!enabled)return;const load=()=>{if(document.visibilityState!=='hidden')refresh().catch(()=>{});};load();const timer=setInterval(load,15000);window.addEventListener('shopping-updated',load);window.addEventListener('focus',load);return()=>{sequence.current++;clearInterval(timer);window.removeEventListener('shopping-updated',load);window.removeEventListener('focus',load);};},[user?.id,enabled]);
 const held=(item,row)=>{const quantity=row.quantity||1;const availability=item.availability||{reserved:0,purchased:0,available:1};const updated={...item,availability:{...availability,reserved:availability.reserved+quantity,available:Math.max(0,availability.available-quantity),held_by_you:true}};setRows(current=>[{...row,is_owner:true,item:updated,status:'reserved'},...current.filter(r=>r.id!==row.id)]);setItems(current=>({...current,[item.id]:updated}));};
 const changed=(row,status)=>{const a=row.item.availability||{reserved:row.quantity,purchased:0,available:0};const updated={...row.item,availability:{...a,reserved:Math.max(0,a.reserved-row.quantity),purchased:a.purchased+(status==='purchased'?row.quantity:0),available:a.available+(status==='cancelled'?row.quantity:0),held_by_you:false}};setRows(current=>status==='cancelled'?current.filter(r=>r.id!==row.id):current.map(r=>r.id===row.id?{...r,status,item:updated}:r));setItems(current=>{const next={...current};if(status==='cancelled')delete next[row.item.id];else next[row.item.id]=updated;return next;});};
 return <ShoppingContext.Provider value={{rows,items,loaded,refresh,held,changed}}>{children}</ShoppingContext.Provider>;
}

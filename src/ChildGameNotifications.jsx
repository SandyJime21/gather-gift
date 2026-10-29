import {useEffect,useState} from 'react';
import {Button,Card} from 'react-bootstrap';
import {api} from './lib/api.js';
export default function ChildGameNotifications(){
 const [rows,setRows]=useState([]);
 const load=()=>api('/child/game-notifications').then(r=>setRows(r.notifications)).catch(()=>{});
 useEffect(()=>{load();const timer=setInterval(load,15000);window.addEventListener('focus',load);return()=>{clearInterval(timer);window.removeEventListener('focus',load);};},[]);
 const read=async id=>{await api('/child/game-notifications/'+id+'/read',{method:'POST',body:JSON.stringify({})});load();};
 if(!rows.length)return null;
 return <section className="mb-4" aria-label="Game notifications"><h2 className="h5">Game invitations</h2>{rows.map(row=><Card key={row.id} className="mb-2"><Card.Body className="d-flex justify-content-between align-items-center gap-2"><span>{row.message}</span>{!row.read&&<Button size="sm" onClick={()=>read(row.id).catch(()=>{})}>Mark read</Button>}</Card.Body></Card>)}</section>;
}

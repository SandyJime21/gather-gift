import {Button} from 'react-bootstrap';
export default function TicketHouseholds({ticket,onRequest,superuser=false}){
 const homes=ticket.households||[];
 return <div className="my-2">{homes.length?homes.map(home=><div key={home.id} className="d-flex gap-2 align-items-center flex-wrap mb-2"><span>{home.name} · Household ID: <strong>{home.id}</strong></span><Button size="sm" variant="outline-success" onClick={()=>onRequest(home,ticket)}>{superuser?'Impersonate':'Impersonate / request access'}</Button></div>):<small className="text-secondary">No family household is currently linked to this requester.</small>}{!homes.length&&superuser&&<Button size="sm" onClick={()=>onRequest({id:null},ticket)}>Impersonate</Button>}<p className="small text-secondary mb-0">{superuser?'Superuser user views are read-only and audited. No owner approval is required.':'This fills your access request. The household owner must approve before you can inspect family data.'}</p></div>;
}

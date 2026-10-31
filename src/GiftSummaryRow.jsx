import GiftDetails from './GiftDetails.jsx';
import {useState} from 'react';
import {Button,Modal} from 'react-bootstrap';
import {Link} from 'react-router-dom';
import {mediaUrl} from './lib/api.js';

export default function GiftSummaryRow({item,actions,details}){
 const [open,setOpen]=useState(false),[failed,setFailed]=useState(false);
 const image=item.image_path||item.image_url;
 const price=item.estimated_price!==''&&item.estimated_price!=null?(item.currency||'USD')+' '+Number(item.estimated_price).toFixed(2):null;
 return <><div className="gift-summary-row"><button type="button" className="gift-summary-image" aria-label={'View '+item.name} onClick={()=>setOpen(true)}>{image&&!failed?<img src={mediaUrl(image)} alt="" loading="lazy" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>:<span aria-hidden="true">🎁</span>}</button><div className="gift-summary-copy"><h3 className="item-title" title={item.name}><Button type="button" variant="link" className="gift-summary-name" title={item.name} onClick={()=>setOpen(true)}>{item.name}</Button></h3>{item.availability?.available===0&&<small>{item.availability.reserved>0?'On hold':'SOLD'}</small>}{item.recipient&&<small>{item.profile_id?<Link to={'/profiles/'+item.profile_id}>{item.recipient}</Link>:item.recipient}</small>}{item.store_name&&<small>{item.store_name}</small>}{price&&<strong title="Estimated price; confirm at the store">{price}</strong>}</div></div>{actions&&<div className="gift-summary-actions">{actions}</div>}<Modal show={open} onHide={()=>setOpen(false)} centered scrollable><Modal.Header closeButton><Modal.Title>{item.name}</Modal.Title></Modal.Header><Modal.Body>{details||<>{image&&<img src={mediaUrl(image)} alt={item.name} className="gift-details-image"/>}<GiftDetails item={item}/></>}</Modal.Body></Modal></>;
}

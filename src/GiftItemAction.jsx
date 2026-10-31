import {useState} from 'react';
import {Button,Modal} from 'react-bootstrap';
import EditGiftDialog from './EditGiftDialog.jsx';
import GiftDetails from './GiftDetails.jsx';

export default function GiftItemAction({item,onSaved}){
 const [open,setOpen]=useState(false);
 const editable=Boolean(item.can_edit);
 return <><Button size="sm" variant="outline-secondary" aria-label={editable?'Edit gift':'View gift'} title={editable?'Edit this gift directly':'View this gift\u2019s details'} onClick={()=>setOpen(true)}>{editable?<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m16 3 5 5-12 12-6 1 1-6L16 3ZM13 6l5 5"/></svg>:'View gift'}</Button>{editable?<EditGiftDialog item={open?item:null} endpoint={item.personal_wish_id?'/personal-wishes/'+item.personal_wish_id:undefined} onClose={()=>setOpen(false)} onSaved={onSaved}/>:<Modal show={open} onHide={()=>setOpen(false)} centered scrollable><Modal.Header closeButton><Modal.Title>{item.name}</Modal.Title></Modal.Header><Modal.Body><GiftDetails item={item}/></Modal.Body></Modal>}</>;
}

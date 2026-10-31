import MoveGiftList from './MoveGiftList.jsx';
import {Modal} from 'react-bootstrap';
import ManualGiftEntry from './ManualGiftEntry.jsx';
import {api} from './lib/api.js';

export default function EditGiftDialog({item,onClose,onSaved,endpoint}){
 if(!item)return null;
 return <Modal show onHide={onClose} centered scrollable><Modal.Header closeButton><Modal.Title>Edit gift</Modal.Title></Modal.Header><Modal.Body><ManualGiftEntry key={item.id} hideTrigger initiallyOpen saveLabel="Save gift" destination="Update this gift's details" initialGift={{name:item.name,description:item.description||'',desired_size:item.desired_size||'',desired_color:item.desired_color||'',quantity:item.quantity||1,priority:item.priority||2,category:item.category||'',estimated_price:item.estimated_price??'',currency:item.currency||'USD',store_name:item.store_name||'',product_url:item.original_product_url||item.product_url||''}} onSave={async gift=>{await api(endpoint||'/items/'+item.id,{method:'PATCH',body:JSON.stringify(gift)});window.dispatchEvent(new Event('wishlist-updated'));await onSaved?.();onClose();}} onDone={onClose}/><MoveGiftList item={{...item,can_edit:true}} onMoved={onSaved}/></Modal.Body></Modal>;
}

import {useEffect,useState} from 'react';
import {Alert,Button,Dropdown,Form} from 'react-bootstrap';
import {Link} from 'react-router-dom';

export function inBudget(item,{minimum='',maximum='',currency='USD'}={}){
 if(minimum==='' && maximum==='')return true;
 const raw=item.estimated_price;
 if(raw===null || raw===undefined || String(raw).trim()==='')return false;
 const price=Number(raw),low=minimum===''?0:Number(minimum),high=maximum===''?Infinity:Number(maximum);
 return Number.isFinite(price)&&price>=0&&Number.isFinite(low)&&low>=0&&high>=low&&(Number.isFinite(high)||maximum==='')&&(item.currency||'USD').toUpperCase()===currency&&price>=low&&price<=high;
}
export const priceBands=[{label:'Under 25',min:0,max:25},{label:'25 to 49.99',min:25,max:50},{label:'50 to 99.99',min:50,max:100},{label:'100 and up',min:100,max:Infinity}];
export function coveredPriceBands(items,currency='USD'){
 return priceBands.map(band=>({...band,covered:items.some(item=>{const price=Number(item.estimated_price);return item.estimated_price!==null&&item.estimated_price!==undefined&&String(item.estimated_price).trim()!==''&&Number.isFinite(price)&&price>=band.min&&price<band.max&&(item.currency||'USD').toUpperCase()===currency;})}));
}
export function BudgetFilters({minimum,maximum,currency,onMinimum,onMaximum,onCurrency,onClear,prefix='budget',children}){
 return <Dropdown autoClose="outside" className="mb-3"><Dropdown.Toggle title="Narrow the gifts by budget, currency, and the available filters." variant="outline-success">Filter{minimum!==''||maximum!==''?' ? Budget set':''}</Dropdown.Toggle><Dropdown.Menu className="p-3" style={{width:'min(360px, calc(100vw - 40px))'}}>{children}<fieldset className="border-0 p-0"><legend className="fs-6">Budget</legend><Form.Group controlId={prefix+'-range'} className="mb-3"><Form.Label>Price range</Form.Label><Form.Select value={minimum===''&&['','25','50','100'].includes(maximum)?maximum:'custom'} onChange={e=>{if(e.target.value==='custom'){onMinimum('0');return;}onMinimum('');onMaximum(e.target.value);}}><option value="">All prices</option><option value="25">Up to 25</option><option value="50">Up to 50</option><option value="100">Up to 100</option><option value="custom">Custom range</option></Form.Select></Form.Group><div className="d-flex gap-2 flex-wrap"><Form.Group controlId={prefix+'-min'}><Form.Label>Minimum price</Form.Label><Form.Control type="number" min="0" step=".01" value={minimum} onChange={e=>onMinimum(e.target.value)} placeholder="Any"/></Form.Group><Form.Group controlId={prefix+'-max'}><Form.Label>Maximum price</Form.Label><Form.Control type="number" min="0" step=".01" value={maximum} onChange={e=>onMaximum(e.target.value)} placeholder="No limit"/></Form.Group><Form.Group controlId={prefix+'-currency'}><Form.Label>Currency</Form.Label><Form.Select value={currency} onChange={e=>onCurrency(e.target.value)}>{['USD','CAD','EUR','GBP','AUD','NZD','JPY','INR'].map(code=><option key={code}>{code}</option>)}</Form.Select></Form.Group></div><div className="d-flex gap-2 flex-wrap mt-2"><Button size="sm" type="button" variant="outline-secondary" onClick={onClear}>No budget / show all prices</Button></div><p className="small text-secondary mt-2 mb-0">{minimum!==''||maximum!==''?'Only gifts with a known price in this currency and range are shown. Shipping and tax may add to the total.':'No budget set. Gifts at all prices, including those without a price, are shown.'}</p>{minimum!==''&&maximum!==''&&Number(minimum)>Number(maximum)&&<p role="alert" className="text-danger small">Minimum price must be no more than maximum price.</p>}</fieldset></Dropdown.Menu></Dropdown>;
}
export function WishlistBudgetSuggestions({items=[],enabled=true,onChange}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const currency=(items.find(item=>item.estimated_price!=null && item.currency)?.currency||'USD').toUpperCase();
 const bands=coveredPriceBands(items,currency);
 if(!enabled || bands.every(band=>band.covered))return null;
 return <Alert variant="light" className="border" aria-label="Wishlist price reminder"><div className="d-flex justify-content-between gap-3"><strong>Help friends find a gift in their budget</strong><Button variant="link" size="sm" disabled={busy} onClick={async()=>{setBusy(true);try{await onChange(false);}catch(e){setError(e.message);}finally{setBusy(false);}}}>Ignore</Button></div><p className="small">Optional: add wishes at different prices. Each range checks off automatically.</p><ul className="list-unstyled mb-0">{bands.map(band=><li className="d-flex justify-content-between align-items-center gap-3 mb-2" key={band.min}><span>{band.covered?'\u2713':'\u25cb'} {currency} {band.label}</span>{band.covered?<small>Added</small>:<Button as={Link} size="sm" variant="outline-success" to={'/discover?add=1&min_price='+band.min+(Number.isFinite(band.max)?'&max_price='+(band.max-.01):'')+'&currency='+currency}>Add gifts</Button>}</li>)}</ul>{error&&<p role="alert">{error}</p>}</Alert>;
}
export function WishlistBudgetPreference({enabled=true,onChange}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 return <section className="my-4"><h2 className="fs-5">Wishlist price suggestions</h2><Form.Check type="switch" id="wishlist-price-suggestions" label="Suggest adding gifts for all budgets" checked={enabled} disabled={busy} onChange={async e=>{const next=e.target.checked;setBusy(true);setError('');try{await onChange(next);}catch(err){setError(err.message);}finally{setBusy(false);}}}/><p className="small text-secondary">This is optional. Turning suggestions off never limits what you can add or how you shop.</p>{error&&<Alert variant="danger">{error}</Alert>}</section>;
}

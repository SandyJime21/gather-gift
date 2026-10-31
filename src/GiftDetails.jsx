import MoveGiftList from './MoveGiftList.jsx';
import AffiliateDisclosure from './AffiliateDisclosure.jsx';
export default function GiftDetails({item}){
 const fields=[['Store',item.store_name],['Estimated price',item.estimated_price!=null&&item.estimated_price!==''?(item.currency||'USD')+' '+Number(item.estimated_price).toFixed(2):null],['Size',item.desired_size],['Color',item.desired_color],['Quantity',item.quantity],['Category',item.category],['Want level',item.priority?item.priority+' of 4':null],['Type',item.request_type?.replaceAll('_',' ')],['Notes',item.notes]];
 return <>{item.description&&<p>{item.description}</p>}<dl>{fields.filter(([,value])=>value!=null&&value!=='').map(([label,value])=><div key={label} className="mb-2"><dt>{label}</dt><dd className="mb-0">{value}</dd></div>)}</dl>{item.product_url&&<a href={item.shopping_url||item.product_url} target="_blank" rel="noopener noreferrer">View at store</a>}{item.product_url&&<AffiliateDisclosure/>}<MoveGiftList item={item}/></>;
}

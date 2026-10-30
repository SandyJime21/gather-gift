import catalog from '../data/affiliate-stores.json';
export const storeCatalog=[...catalog].sort((a,b)=>Number(b.affiliate_approved===true)-Number(a.affiliate_approved===true));
export function findStore(name){const value=(name||'').trim().toLowerCase().replace(/^www\./,'');return storeCatalog.find(store=>[store.name.toLowerCase(),store.domain].includes(value));}
export function storeLogo(store){return store.logo_url||'https://www.google.com/s2/favicons?domain='+encodeURIComponent(store.domain)+'&sz=64';}
export function orderProducts(products){return [...products].sort((a,b)=>Number(findStore(b.store_name)?.affiliate_approved===true)-Number(findStore(a.store_name)?.affiliate_approved===true));}

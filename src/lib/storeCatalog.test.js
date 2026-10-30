import {expect,it} from 'vitest';
import {findStore,orderProducts,storeCatalog} from './storeCatalog.js';
it('does not claim affiliate approval for pending stores and recognizes their domains',()=>{
 expect(storeCatalog.every(store=>typeof store.affiliate_approved==='boolean')).toBe(true);
 expect(findStore('target.com').name).toBe('Target');
 const products=[{store_name:'Target'},{store_name:'Amazon'}];
 expect(orderProducts(products)).toEqual(products);
});

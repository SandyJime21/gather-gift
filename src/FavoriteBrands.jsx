import StoreLogo from './StoreLogo.jsx';
export default function FavoriteBrands({profiles=[]}){
 const brands=new Map();
 for(const profile of profiles){
  const favorites=(profile.preferences||profile).favorite_brands||[];
  for(const value of favorites){
   const name=typeof value==='string'?value.trim():'';
   if(!name||/^(none|no preference|n\/a)$/i.test(name))continue;
   const key=name.toLowerCase(),entry=brands.get(key)||{name,people:new Map()};
   entry.people.set(profile.id??profile.display_name,profile.display_name);
   brands.set(key,entry);
  }
 }
 return <section className="mb-4"><h2>Favorite brands</h2>{brands.size?<div className="favorite-brand-tiles">{[...brands].map(([key,brand])=><article key={key} className="favorite-brand-tile"><StoreLogo name={brand.name}/><strong>{brand.name}</strong><small>{[...brand.people.values()].filter(Boolean).join(', ')}{brand.people.size===1?'\u2019s favorite':' love this'}</small></article>)}</div>:<p className="small text-secondary">Favorite brands appear here when your family and people you follow share them.</p>}</section>;
}

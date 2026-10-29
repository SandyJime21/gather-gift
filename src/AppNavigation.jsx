import { Link, useLocation } from 'react-router-dom';
export function AppIcon({name}) {
 const paths={wishes:'M12 21 3.5 12.5a5.3 5.3 0 0 1 7.5-7.5L12 6l1-1a5.3 5.3 0 0 1 7.5 7.5Z',following:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m11 10v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',discover:'m16 8-3 5-5 3 3-5 5-3M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',gifting:'M3 8h18v4H3zM5 12v9h14v-9M12 8v13M12 8H8a3 3 0 1 1 3-3l1 3Zm0 0h4a3 3 0 1 0-3-3l-1 3Z',settings:'m9 3-1 3-3 1-2 3 2 2-1 3 2 3 3-1 3 2 3-2 3 1 2-3-1-3 2-2-2-3-3-1-1-3ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0'};
 return <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.wishes}/></svg>;
}
export default function AppNavigation(){
 const {pathname}=useLocation();
 const entries=[['/','wishes','My wishes'],['/following','following','Following'],['/discover','discover','Discover'],['/gifting','gifting','My gifting'],['/settings','settings','Settings']];
 return <nav className="app-navigation" aria-label="Main navigation">{entries.map(([to,icon,label])=>{const active=to==='/'?['/','/wishlist'].includes(pathname):pathname.startsWith(to)||to==='/following'&&pathname==='/games'||to==='/gifting'&&pathname==='/buying-now';return <Link key={to} to={to} aria-label={label} title={label} aria-current={active?'page':undefined}><AppIcon name={icon}/><span>{label}</span></Link>;})}</nav>;
}

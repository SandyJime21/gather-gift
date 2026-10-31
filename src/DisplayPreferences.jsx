import {api} from './lib/api.js';
import {appearanceDefaults,buttonInk} from './lib/appearance.js';
import {createContext,useContext,useEffect,useState} from 'react';
import {Form} from 'react-bootstrap';
const DisplayContext=createContext(null);
const key='gather-gift-display';
function read(){try{const value=JSON.parse(localStorage.getItem(key)||'{}');return {dark:value.dark===true,size:[100,115,130,150].includes(value.size)?value.size:100};}catch{return {dark:false,size:100};}}
export function DisplayProvider({children}){
 const [preferences,setPreferences]=useState(read);
 const [appearance,setAppearance]=useState(appearanceDefaults),[preview,setPreview]=useState(null);
 useEffect(()=>{let live=true;api('/app-appearance').then(r=>{if(live&&r.appearance)setAppearance(r.appearance);}).catch(()=>{});return()=>{live=false;};},[]);
 useEffect(()=>{const value=preview||appearance,palette=value[preferences.dark?'dark':'light'];for(const [key,color] of Object.entries(palette))document.documentElement.style.setProperty('--gg-'+key,color);document.documentElement.style.setProperty('--gg-button-ink',buttonInk(palette.accent));document.documentElement.setAttribute('data-app-season',value.season);return()=>{for(const key of Object.keys(palette))document.documentElement.style.removeProperty('--gg-'+key);document.documentElement.style.removeProperty('--gg-button-ink');document.documentElement.removeAttribute('data-app-season');};},[appearance,preview,preferences.dark]);
 useEffect(()=>{document.documentElement.setAttribute('data-bs-theme',preferences.dark?'dark':'light');document.documentElement.setAttribute('data-text-size',String(preferences.size));document.documentElement.style.fontSize=preferences.size+'%';try{localStorage.setItem(key,JSON.stringify(preferences));}catch{}},[preferences]);
 useEffect(()=>{const sync=e=>{if(e.key===key)setPreferences(read());};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync);},[]);
 return <DisplayContext.Provider value={{preferences,setPreferences,appearance,setAppearance,setPreview}}>{children}</DisplayContext.Provider>;
}
export function useDisplayPreferences(){return useContext(DisplayContext);}
export default function DisplayPreferences(){
 const {preferences,setPreferences}=useContext(DisplayContext);
 return <section className="settings-card card mb-4"><div className="card-body"><h2>Display &amp; readability</h2><Form.Check type="switch" id="display-dark" label="Dark mode" checked={preferences.dark} onChange={e=>setPreferences(current=>({...current,dark:e.target.checked}))}/><Form.Group controlId="display-text-size" className="mt-3"><Form.Label>Text size</Form.Label><Form.Select value={preferences.size} onChange={e=>setPreferences(current=>({...current,size:Number(e.target.value)}))}>{[[100,'Standard'],[115,'Large'],[130,'Larger'],[150,'Extra large']].map(([value,label])=><option key={value} value={value}>{label} ({value}%)</option>)}</Form.Select><Form.Text>Saved on this browser. Browser zoom and screen readers still work.</Form.Text></Form.Group></div></section>;
}

import {useState} from 'react';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import LetterArtPicker from './LetterArtPicker.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:path=>path}));
beforeEach(()=>api.mockReset());
const designs=[{id:1,name:'Snowflakes',price_cents:0,unlocked:true,background:'#fff',foreground:'#222',accent:'#123'},{id:2,name:'Santa stars',price_cents:300,unlocked:false,background:'#fff',foreground:'#222',accent:'#123'}];
function Picker(){const [value,setValue]=useState(null);return <LetterArtPicker householdId={9} value={value} onChange={setValue}/>;}
it('shows free and USD prices and allows paid art previews without granting an unlock',async()=>{
 api.mockResolvedValue({designs,checkout_enabled:false});
 render(<Picker/>);
 fireEvent.click(await screen.findByRole('button',{name:'Snowflakes Free'}));
 expect(screen.getByRole('button',{name:'Snowflakes Free'})).toHaveAttribute('aria-pressed','true');
 fireEvent.click(screen.getByRole('button',{name:'Santa stars $3.00'}));
 expect(screen.getByRole('button',{name:'Santa stars $3.00'})).toHaveAttribute('aria-pressed','true');
 expect(screen.getByRole('button',{name:'Unlock for $3.00'})).toBeDisabled();
});
it('marks a paid design ready only after the server confirms the family unlock',async()=>{
 const available=vi.fn();
 api.mockResolvedValue({designs:[{...designs[1],unlocked:true}],checkout_enabled:true});
 render(<LetterArtPicker householdId={9} value={2} onChange={()=>{}} onAvailabilityChange={available}/>);
 await waitFor(()=>expect(available).toHaveBeenLastCalledWith(true));
 expect(screen.getByRole('button',{name:'Santa stars Unlocked for your family'})).toHaveAttribute('aria-pressed','true');
 expect(screen.queryByRole('button',{name:'Unlock for $3.00'})).not.toBeInTheDocument();
});

import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi,beforeEach} from 'vitest';
import {ThemeStudio} from './SharedThemes.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:path=>path}));
beforeEach(()=>api.mockReset());
it('lets the developer publish letter art with a three-dollar family price',async()=>{
 api.mockResolvedValue({themes:[]});
 render(<ThemeStudio/>);
 fireEvent.change(screen.getByLabelText('This design is for'),{target:{value:'letter'}});
 fireEvent.change(screen.getByLabelText('Design name'),{target:{value:'Santa stars'}});
 fireEvent.change(screen.getByLabelText('Letter art price'),{target:{value:'paid'}});
 expect(screen.getByLabelText('Price (USD)')).toHaveValue(3);
 fireEvent.submit(screen.getByLabelText('Design name').closest('form'));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/support/themes',expect.objectContaining({method:'POST'})));
 const body=api.mock.calls.find(([,options])=>options?.method==='POST')[1].body;
 expect(body.get('purpose')).toBe('letter');expect(body.get('price')).toBe('3.00');
});
it('lets the developer change a published letter design to free',async()=>{
 api.mockResolvedValue({themes:[{id:4,name:'Santa stars',purpose:'letter',price_cents:300,audience:'everyone',background:'#fff5ee',foreground:'#332244',accent:'#775599',active:true}]});
 render(<ThemeStudio/>);
 fireEvent.click(await screen.findByRole('button',{name:'Edit design / price'}));
 fireEvent.change(screen.getByLabelText('Letter art price'),{target:{value:'free'}});
 fireEvent.submit(screen.getByLabelText('Design name').closest('form'));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/support/themes/4',expect.objectContaining({method:'PATCH'})));
 const body=api.mock.calls.find(([,options])=>options?.method==='PATCH')[1].body;
 expect(body.get('price')).toBe('0');
});

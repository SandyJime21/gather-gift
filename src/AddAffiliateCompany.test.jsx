import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import AddAffiliateCompany from './AddAffiliateCompany.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('adds a company with a public ID and server key reference without assuming approval',async()=>{
 api.mockResolvedValue({provider:{}});const saved=vi.fn();
 render(<AddAffiliateCompany onSaved={saved}/>);
 fireEvent.click(screen.getByRole('button',{name:'Add affiliate company'}));
 fireEvent.change(screen.getByLabelText('Company name'),{target:{value:'My shop'}});
 fireEvent.change(screen.getByLabelText('Company / store website'),{target:{value:'https://shop.example'}});
 fireEvent.change(screen.getByLabelText('API key environment variable name (optional)'),{target:{value:'MY_SHOP_API_KEY'}});
 fireEvent.click(screen.getByRole('button',{name:'Save company'}));
 await waitFor(()=>expect(saved).toHaveBeenCalled());
 const payload=JSON.parse(api.mock.calls[0][1].body);
 expect(payload).toMatchObject({company_name:'My shop',key_environment:'MY_SHOP_API_KEY',approved:false,enabled:false});
 expect(payload).not.toHaveProperty('api_key');
});

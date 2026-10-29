import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PriceComparison } from './App.jsx';
import { api } from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),clearCsrfToken:vi.fn(),mediaUrl:path=>path}));
afterEach(()=>vi.clearAllMocks());
it('compares priced offers on demand without claiming they are identical or include shipping',async()=>{
 api.mockResolvedValue({products:[{name:'Puzzle deluxe',store_name:'Store B',estimated_price:'30',currency:'USD',product_url:'https://b.example/puzzle'},{name:'Puzzle',store_name:'Store A',estimated_price:'20',currency:'USD',product_url:'https://a.example/puzzle',shopping_url:'https://affiliate.example/puzzle'},{name:'Unknown price',estimated_price:'',currency:'USD',product_url:'https://c.example/puzzle'}]});
 render(<MemoryRouter><PriceComparison item={{name:'Puzzle',desired_color:'Blue'}}/></MemoryRouter>);
 expect(api).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Compare prices'}));
 expect(await screen.findByText('Lowest listed price in these results')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/gift-discovery?q=Puzzle%20Blue');
 expect(screen.getAllByRole('link',{name:'View offer'})[0]).toHaveAttribute('href','https://affiliate.example/puzzle');
 expect(screen.queryByText('Unknown price')).not.toBeInTheDocument();
 expect(screen.getByText(/Shipping and tax may change the total/)).toBeInTheDocument();
});

import {fireEvent,render,screen,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {expect,it} from 'vitest';
import GiftSummaryRow from './GiftSummaryRow.jsx';
it('keeps the row concise and reveals all details on click',async()=>{
 render(<MemoryRouter><GiftSummaryRow item={{name:'Puzzle',recipient:'Sam',store_name:'Target',estimated_price:'19.99',currency:'USD',description:'The 500 piece blue edition',product_url:'https://example.com/puzzle'}} actions={<button>Save</button>}/></MemoryRouter>);
 expect(screen.getByText('USD 19.99')).toBeInTheDocument();
 expect(screen.queryByText('The 500 piece blue edition')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'View Puzzle'}));
 const dialog=await screen.findByRole('dialog');
 expect(within(dialog).getByText('The 500 piece blue edition')).toBeInTheDocument();
 expect(within(dialog).getByRole('link',{name:'View at store'})).toHaveAttribute('href','https://example.com/puzzle');
});

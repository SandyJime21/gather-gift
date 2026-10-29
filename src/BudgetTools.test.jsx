import {expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {inBudget,coveredPriceBands,WishlistBudgetSuggestions} from './BudgetTools.jsx';

it('matches inclusive price bounds in the selected currency and excludes unknown prices',()=>{
 const filter={minimum:'10',maximum:'50',currency:'USD'};
 for(const price of [10,25,50])expect(inBudget({estimated_price:price,currency:'USD'},filter)).toBe(true);
 for(const price of [null,undefined,'',9.99,50.01,'NaN'])expect(inBudget({estimated_price:price,currency:'USD'},filter)).toBe(false);
 expect(inBudget({estimated_price:20,currency:'EUR'},filter)).toBe(false);
 expect(inBudget({estimated_price:0,currency:'USD'},{maximum:'0'})).toBe(true);
 expect(inBudget({estimated_price:20},{minimum:'50',maximum:'10'})).toBe(false);
});

it('shows every price and unpriced gifts when no budget is selected',()=>{
 for(const gift of [{estimated_price:null},{estimated_price:10000},{estimated_price:40,currency:'EUR'}])expect(inBudget(gift)).toBe(true);
});

it('treats price-band boundaries separately and never treats unknown prices as free gifts',()=>{
 expect(coveredPriceBands([{estimated_price:null}]).map(b=>b.covered)).toEqual([false,false,false,false]);
 expect(coveredPriceBands([{estimated_price:25}]).map(b=>b.covered)).toEqual([false,true,false,false]);
 expect(coveredPriceBands([0,25,50,100].map(estimated_price=>({estimated_price})))).toHaveLength(4);
 expect(coveredPriceBands([0,25,50,100].map(estimated_price=>({estimated_price}))).every(b=>b.covered)).toBe(true);
});

it('checks covered bands, links missing bands to filtered search, and lets people ignore the reminder',async()=>{
 const change=vi.fn().mockResolvedValue(undefined);
 const view=render(<MemoryRouter><WishlistBudgetSuggestions items={[{estimated_price:10,currency:'USD'}]} onChange={change}/></MemoryRouter>);
 expect(screen.getByText('Added')).toBeInTheDocument();
 const links=screen.getAllByRole('button',{name:'Add gifts'});
 expect(links).toHaveLength(3);
 expect(links[0]).toHaveAttribute('href','/discover?add=1&min_price=25&max_price=49.99&currency=USD');
 fireEvent.click(screen.getByRole('button',{name:'Ignore'}));
 await waitFor(()=>expect(change).toHaveBeenCalledWith(false));
 view.rerender(<MemoryRouter><WishlistBudgetSuggestions enabled={false} onChange={change}/></MemoryRouter>);
 expect(screen.queryByLabelText('Wishlist price reminder')).not.toBeInTheDocument();
 view.rerender(<MemoryRouter><WishlistBudgetSuggestions items={[10,30,60,120].map(estimated_price=>({estimated_price,currency:'USD'}))} onChange={change}/></MemoryRouter>);
 expect(screen.queryByLabelText('Wishlist price reminder')).not.toBeInTheDocument();
});

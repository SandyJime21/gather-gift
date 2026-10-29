import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import AppNavigation from './AppNavigation.jsx';
it('has five labeled icon destinations and marks Following active for games',()=>{
 render(<MemoryRouter initialEntries={['/games?create=1']}><AppNavigation/></MemoryRouter>);
 expect(screen.getAllByRole('link')).toHaveLength(5);
 for(const name of ['My wishes','Following','Discover','Saved items','Settings'])expect(screen.getByRole('link',{name}).querySelector('svg')).toBeTruthy();
 expect(screen.getByRole('link',{name:'Following'})).toHaveAttribute('aria-current','page');
 expect(screen.getByRole('link',{name:'Discover'})).toHaveAttribute('href','/discover');
});

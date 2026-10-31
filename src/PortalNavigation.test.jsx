import {fireEvent,render,screen} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import PortalNavigation from './PortalNavigation.jsx';
it('keeps ordinary support navigation separate from superuser tools',()=>{
 const select=vi.fn();render(<PortalNavigation section="access" onSelect={select} superuser={false}/>);
 expect(screen.getByRole('button',{name:'Support workspace'})).toHaveAttribute('aria-current','page');
 expect(screen.queryByRole('button',{name:'User accounts'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Portal menu'}));
 expect(screen.getByRole('button',{name:'Portal menu'})).toHaveAttribute('aria-expanded','true');
 fireEvent.click(screen.getByRole('button',{name:'Activity & diagnostics'}));
 expect(select).toHaveBeenCalledWith('logs');
 expect(screen.getByRole('button',{name:'Portal menu'})).toHaveAttribute('aria-expanded','false');
});
it('shows one destination per superuser tool',()=>{
 render(<PortalNavigation section="accounts" onSelect={()=>{}} superuser/>);
 expect(screen.getAllByRole('button',{name:'Support workspace'})).toHaveLength(1);
 expect(screen.getByRole('button',{name:'User accounts'})).toHaveAttribute('aria-current','page');
 expect(screen.getByRole('button',{name:'Themes & list artwork'})).toBeInTheDocument();
});

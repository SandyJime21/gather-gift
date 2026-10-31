import {fireEvent,render,screen} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import TicketHouseholds from './TicketHouseholds.jsx';
it('shows family IDs and prefills access through a callback without sending a request',()=>{
 const request=vi.fn(),ticket={id:3,subject:'Help',households:[{id:9,name:'Gonzales family'}]};
 render(<TicketHouseholds ticket={ticket} onRequest={request}/>);
 expect(screen.getByText('9')).toBeInTheDocument();
 expect(request).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Impersonate / request access'}));
 expect(request).toHaveBeenCalledWith({id:9,name:'Gonzales family'},ticket);
});

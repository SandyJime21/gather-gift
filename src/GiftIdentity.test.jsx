import { fireEvent, render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { GiftIdentity } from './App.jsx';

describe('gift status overlay', () => {
  it('marks fully purchased gifts with an image overlay', () => {
    render(<GiftIdentity item={{ name: 'Puzzle', image_url: 'https://example.com/image.jpg', availability: { available: 0, purchased: 1, reserved: 0 } }} />);
    expect(screen.getByText('SOLD')).toBeInTheDocument();
    expect(screen.getByText('SOLD').closest('.gift-status-overlay')).toBeInTheDocument();
  });
  it('distinguishes temporary holds from purchases even without a photo', () => {
    render(<GiftIdentity item={{ name: 'Puzzle', availability: { available: 0, purchased: 0, reserved: 1 } }} />);
    expect(screen.getByText('On hold')).toBeInTheDocument();
    expect(screen.queryByText('SOLD')).not.toBeInTheDocument();
  });
  it('keeps partial quantities available and hides status from recipients', () => {
    const { rerender } = render(<GiftIdentity item={{ name: 'Puzzle', availability: { available: 1, purchased: 1, reserved: 0 } }} />);
    expect(screen.queryByText('SOLD')).not.toBeInTheDocument();
    rerender(<GiftIdentity item={{ name: 'Puzzle' }} />);
    expect(screen.queryByText('SOLD')).not.toBeInTheDocument();
    expect(screen.queryByText('On hold')).not.toBeInTheDocument();
  });
});

it('keeps the guide out of gift cards until the recipient help button is opened',async()=>{
 render(<GiftIdentity item={{name:'Puzzle',recipient:'Mia',recipient_photo_path:'/mia.jpg',recipient_preferences:{allergies:'Peanuts',clothing_sizes:{shirt:'5T'},favorite_colors:['Pink'],favorite_characters:['Minnie Mouse'],favorite_stores:['Toy shop']}}}/>);
 expect(screen.queryByRole('img',{name:'Gift for Mia'})).not.toBeInTheDocument();
 expect(screen.queryByText('Peanuts')).not.toBeInTheDocument();
 const button=screen.getByRole('button',{name:"Mia's gift guide"});
 expect(button).toHaveAttribute('title',"Mia's gift guide");
 fireEvent.click(button);
 expect(await screen.findByRole('dialog')).toBeInTheDocument();
 for(const value of ['Peanuts','shirt: 5T','Pink','Minnie Mouse','Toy shop'])expect(screen.getByText(value)).toBeInTheDocument();
});

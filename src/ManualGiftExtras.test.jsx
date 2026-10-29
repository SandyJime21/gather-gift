import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ManualGiftExtras } from "./App.jsx";
import { api } from "./lib/api.js";
vi.mock("./lib/api.js", () => ({ api: vi.fn(), clearCsrfToken: vi.fn(), mediaUrl: (path) => path }));
afterEach(() => vi.clearAllMocks());
describe('manual gift preview', () => {
  it('uses the link image while preserving a manually entered title', async () => {
    api.mockResolvedValueOnce({ preview: { title: 'Store title', image_url: 'https://example.com/gift.jpg', store_name: 'Store' } });
    const onChange = vi.fn();
    render(<ManualGiftExtras gift={{ name: 'My own title', product_url: 'https://example.com/product' }} recipient="Mia" onChange={onChange} />);
    expect(screen.getByRole('heading', { name: 'My own title' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Preview link image' }));
    expect(await screen.findByText('Link image added to your gift preview.')).toBeInTheDocument();
    expect(onChange).toHaveBeenCalledWith({ name: 'My own title', product_url: 'https://example.com/product', image_url: 'https://example.com/gift.jpg', store_name: 'Store' });
    expect(screen.getByRole('button', { name: 'Buy' })).toBeDisabled();
  });
});

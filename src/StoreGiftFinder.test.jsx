import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StoreGiftFinder } from "./App.jsx";
import { api } from "./lib/api.js";
vi.mock("./lib/api.js", () => ({ api: vi.fn(), clearCsrfToken: vi.fn(), mediaUrl: (path) => path }));
afterEach(() => vi.clearAllMocks());

describe("store gift finder", () => {
  it("fills a gift and store search link without requiring a pasted URL", () => {
    const onChange = vi.fn();
    render(<StoreGiftFinder gift={{ name: "", store_name: "", product_url: "" }} onChange={onChange} />);
    expect(screen.getAllByRole("button", { name: "Use this store" })[0]).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Search for a gift"), { target: { value: "LEGO flowers" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Use this store" })[0]);
    expect(onChange).toHaveBeenCalledWith({ name: "LEGO flowers", store_name: "Walmart", product_url: "https://www.walmart.com/search?q=LEGO%20flowers" });
    expect(screen.getAllByRole("link", { name: /Browse store/ })).toHaveLength(8);
  });
});


describe("live gift discovery", () => {
  it("fills exact product details from a selected search result", async () => {
    api.mockResolvedValueOnce({ enabled: true, products: [{ name: "Flower building set", store_name: "Example Store", estimated_price: "24.99", currency: "USD", product_url: "https://store.example.com/flowers" }] });
    const onChange = vi.fn();
    render(<StoreGiftFinder gift={{ name: "", priority: "2" }} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Search for a gift"), { target: { value: "flowers" } });
    fireEvent.click(screen.getByRole("button", { name: "Find gifts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Use this gift" }));
    expect(onChange).toHaveBeenCalledWith({ name: "Flower building set", priority: "2", store_name: "Example Store", estimated_price: "24.99", currency: "USD", product_url: "https://store.example.com/flowers", image_url: "" });
  });
  it("keeps Google browsing available when live product search is not configured", async () => {
    api.mockResolvedValueOnce({ enabled: false, products: [], message: "Live product results are not available yet." });
    render(<StoreGiftFinder gift={{ name: "" }} onChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Search for a gift"), { target: { value: "building sets" } });
    fireEvent.click(screen.getByRole("button", { name: "Find gifts" }));
    expect(await screen.findByText("Live product results are not available yet.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Browse store" }).some((link) => link.href === "https://www.google.com/search?tbm=shop&q=building%20sets")).toBe(true);
    expect(screen.queryByRole("button", { name: "Use this gift" })).not.toBeInTheDocument();
  });
});

describe('gift inspiration categories', () => {
  it('starts a stocking-stuffer search without copying a link', () => {
    const onChange = vi.fn();
    render(<StoreGiftFinder gift={{ name: '', product_url: '', store_name: '' }} onChange={onChange} />);
    expect(screen.getByLabelText('Gift category')).toHaveValue('everyday');
    expect(screen.queryByRole('button', { name: 'Mini puzzles' })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Gift category'), { target: { value: 'stocking' } });
    fireEvent.click(screen.getByRole('button', { name: 'Mini puzzles' }));
    expect(screen.getByLabelText('Search for a gift')).toHaveValue('Mini puzzles');
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ name: 'Mini puzzles', category: 'Stocking stuffers' }));
    expect(screen.getAllByRole('link', { name: 'Browse store' })[0]).toHaveAttribute('href', 'https://www.walmart.com/search?q=Mini%20puzzles');
  });
});


describe('quick wishlist saving', () => {
  it('saves multiple products without leaving search and prevents repeat saves', async () => {
    api.mockResolvedValueOnce({ products: [
      { name: 'Puzzle', product_url: 'https://store.example.com/puzzle', thumbnail: 'https://store.example.com/puzzle.jpg' },
      { name: 'Book', product_url: 'https://store.example.com/book' },
    ] });
    const onSaveProduct = vi.fn().mockResolvedValue(undefined);
    render(<StoreGiftFinder gift={{ name: '' }} onChange={vi.fn()} onSaveProduct={onSaveProduct} />);
    fireEvent.change(screen.getByLabelText('Search for a gift'), { target: { value: 'gifts' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find gifts' }));
    fireEvent.click((await screen.findAllByRole('button', { name: /Save to list/ }))[0]);
    expect(await screen.findByRole('button', { name: 'Saved to list' })).toBeDisabled();
    expect(onSaveProduct).toHaveBeenCalledWith(expect.objectContaining({ name: 'Puzzle', image_url: 'https://store.example.com/puzzle.jpg' }));
    fireEvent.click(screen.getByRole('button', { name: /Save to list/ }));
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Saved to list' })).toHaveLength(2));
    expect(onSaveProduct).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('button', { name: 'Use this gift' })).not.toBeInTheDocument();
  });
  it('keeps failed saves retryable', async () => {
    api.mockResolvedValueOnce({ products: [{ name: 'Puzzle', product_url: 'https://store.example.com/puzzle' }] });
    const onSaveProduct = vi.fn().mockRejectedValue(new Error('Save failed'));
    render(<StoreGiftFinder gift={{ name: '' }} onChange={vi.fn()} onSaveProduct={onSaveProduct} />);
    fireEvent.change(screen.getByLabelText('Search for a gift'), { target: { value: 'puzzle' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find gifts' }));
    fireEvent.click(await screen.findByRole('button', { name: /Save to list/ }));
    expect(await screen.findByText('Save failed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save to list/ })).toBeEnabled();
  });
});


it('allows undoing an unheart without deleting the original wish', async () => {
  api.mockResolvedValueOnce({ products: [{ name: 'Puzzle', product_url: 'https://store.example.com/puzzle' }] });
  const remove = vi.fn();
  render(<StoreGiftFinder gift={{ name: '' }} onChange={vi.fn()} onSaveProduct={vi.fn()} onRemoveProduct={remove} savedUrls={['https://store.example.com/puzzle']} />);
  fireEvent.change(screen.getByLabelText('Search for a gift'), { target: { value: 'puzzle' } });
  fireEvent.click(screen.getByRole('button', { name: 'Find gifts' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Unheart / remove' }));
  expect(screen.getByText(/Removed Puzzle from your list/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Undo' }));
  expect(screen.getByRole('button', { name: 'Unheart / remove' })).toHaveAttribute('aria-pressed', 'true');
  expect(remove).not.toHaveBeenCalled();
  expect(screen.queryByRole('button', { name: 'Undo' })).not.toBeInTheDocument();
});


it('previews a pasted link and saves its details without manual gift inputs', async () => {
  api.mockResolvedValueOnce({ preview: { title: 'Cozy blanket', image_url: 'https://store.example.com/blanket.jpg', store_name: 'Example Store' } });
  const save = vi.fn().mockResolvedValue(undefined);
  render(<StoreGiftFinder gift={{ name: '' }} onChange={vi.fn()} onSaveProduct={save} />);
  fireEvent.change(screen.getByLabelText('Search for a gift'), { target: { value: 'https://store.example.com/blanket' } });
  fireEvent.click(screen.getByRole('button', { name: 'Preview link' }));
  fireEvent.click(await screen.findByRole('button', { name: /Save to list/ }));
  await screen.findByRole('button', { name: 'Saved to list' });
  expect(api).toHaveBeenCalledWith('/link-preview', expect.objectContaining({ method: 'POST', body: JSON.stringify({ url: 'https://store.example.com/blanket' }) }));
  expect(save).toHaveBeenCalledWith(expect.objectContaining({ name: 'Cozy blanket', product_url: 'https://store.example.com/blanket', image_url: 'https://store.example.com/blanket.jpg' }));
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { usePhotoCrop } from "./PhotoCropper.jsx";

function Harness({ onResult }) {
  const { crop, cropper } = usePhotoCrop();
  return <><input aria-label="pick" type="file" onChange={async (e) => onResult(await crop(e.target.files[0]))} />{cropper}</>;
}

let originalImage;
beforeEach(() => {
  originalImage = globalThis.Image;
  globalThis.Image = class { set src(value) { this.naturalWidth = 800; this.naturalHeight = 400; setTimeout(() => this.onload?.(), 0); } };
  URL.createObjectURL = vi.fn(() => "blob:photo");
  URL.revokeObjectURL = vi.fn();
  const ctx = { fillRect: vi.fn(), drawImage: vi.fn(), fillStyle: "" };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx);
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((cb, type) => cb(new Blob(["x"], { type })));
});
afterEach(() => { globalThis.Image = originalImage; vi.restoreAllMocks(); });

const pick = () => fireEvent.change(screen.getByLabelText("pick"), { target: { files: [new File(["p"], "me.heic.jpg", { type: "image/jpeg" })] } });

describe("photo cropper", () => {
  it("returns a zoomed square image after the user positions it", async () => {
    const onResult = vi.fn();
    render(<Harness onResult={onResult} />);
    pick();
    expect(await screen.findByText("Position your photo")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Zoom", { selector: "input" }), { target: { value: "2" } });
    fireEvent.click(await screen.findByRole("button", { name: "Use this photo" }));
    await waitFor(() => expect(onResult).toHaveBeenCalled());
    const result = onResult.mock.calls[0][0];
    expect(result).toBeInstanceOf(File);
    expect(result.name).toBe("me.heic.jpg".replace(/\.[^.]+$/, "") + ".jpg");
    expect(result.type).toBe("image/jpeg");
  });

  it("returns null when cancelled", async () => {
    const onResult = vi.fn();
    render(<Harness onResult={onResult} />);
    pick();
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(onResult).toHaveBeenCalledWith(null));
  });
});

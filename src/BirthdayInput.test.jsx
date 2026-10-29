import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BirthdayInput } from "./App.jsx";
function BirthdayForm() {
  const [value, setValue] = useState("");
  return <><BirthdayInput value={value} onChange={setValue} /><output aria-label="Birthday value">{value}</output></>;
}
describe("birthday month and day", () => {
  it("allows February 29 without asking for a year and clears the birthday", () => {
    render(<BirthdayForm />);
    expect(screen.getAllByRole("combobox")).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Birthday month"), { target: { value: "02" } });
    fireEvent.change(screen.getByLabelText("Birthday day"), { target: { value: "29" } });
    expect(screen.getByLabelText("Birthday value")).toHaveTextContent("02-29");
    fireEvent.click(screen.getByRole("button", { name: "Clear birthday" }));
    expect(screen.getByLabelText("Birthday month")).toHaveValue("");
    expect(screen.getByLabelText("Birthday day")).toHaveValue("");
  });
});

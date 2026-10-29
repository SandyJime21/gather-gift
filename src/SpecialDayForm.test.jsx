import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SpecialDayForm } from "./App.jsx";
function Example() {
  const [occasion, setOccasion] = useState({ type: "birthday", profile_id: "", name: "", date: "" });
  return <SpecialDayForm profiles={[{ id: 1, display_name: "Mia", birthday: "05-14" }, { id: 2, display_name: "Sam", birthday: null }]} occasion={occasion} onChange={setOccasion} onSubmit={(e) => e.preventDefault()} />;
}
describe("family special days", () => {
  it("populates members, defaults Christmas to All family, and fills a person's birthday", () => {
    render(<Example />);
    expect(screen.getByRole("option", { name: "Mia" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sam" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Occasion"), { target: { value: "christmas" } });
    expect(screen.getByLabelText("For")).toHaveValue("all");
    expect(screen.getByLabelText("Name")).toHaveValue("Christmas");
    expect(screen.getByLabelText("Date").value).toMatch(/-12-25$/);
    fireEvent.change(screen.getByLabelText("Occasion"), { target: { value: "birthday" } });
    expect(screen.getByLabelText("For")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("For"), { target: { value: "1" } });
    expect(screen.getByLabelText("Name")).toHaveValue("Mia's Birthday");
    expect(screen.getByLabelText("Date").value).toMatch(/-05-14$/);
    fireEvent.change(screen.getByLabelText("For"), { target: { value: "2" } });
    expect(screen.getByLabelText("Name")).toHaveValue("Sam's Birthday");
    expect(screen.getByLabelText("Date")).toHaveValue("");
  });
});

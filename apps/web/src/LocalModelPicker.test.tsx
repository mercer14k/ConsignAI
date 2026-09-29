import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { LocalModelPicker } from "./LocalModelPicker";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
const models = [
  {
    name: "my-local-model:small",
    size_bytes: 1024 ** 3,
    digest: "fixture",
    parameter_size: "1B",
    quantization: "Q4",
  },
];
function mockCatalog(status = "available", installed = models) {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: true,
        json: async () => ({
          status,
          models: installed,
          excluded_count: 0,
          message:
            status === "unavailable"
              ? "Cannot read local models."
              : "Select a model explicitly.",
        }),
      }),
  );
}
it("never picks the first installed model and requires an explicit selection", async () => {
  mockCatalog();
  const onSelect = vi.fn();
  render(<LocalModelPicker selected={null} onSelect={onSelect} />);
  await screen.findByRole("option", { name: models[0].name });
  expect(screen.getByLabelText("AI model")).toHaveValue("");
  expect(
    screen.getByRole("button", { name: "Use selected model" }),
  ).toBeDisabled();
  expect(onSelect).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("AI model"), {
    target: { value: models[0].name },
  });
  fireEvent.click(screen.getByRole("button", { name: "Use selected model" }));
  expect(onSelect).toHaveBeenCalledWith(models[0].name);
});
it("lets the user clear an existing selection", async () => {
  mockCatalog();
  const onSelect = vi.fn();
  render(<LocalModelPicker selected={models[0].name} onSelect={onSelect} />);
  fireEvent.click(screen.getByRole("button", { name: "Use without AI" }));
  expect(onSelect).toHaveBeenCalledWith(null);
});
it.each(["empty", "unavailable"])(
  "keeps computation available when discovery is %s",
  async (status) => {
    mockCatalog(status, []);
    render(<LocalModelPicker selected={null} onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Refresh models" }),
      ).toBeEnabled(),
    );
    expect(screen.getByLabelText("AI model")).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Use without AI" }),
    ).toBeEnabled();
  },
);
it("cannot apply a model that disappeared during refresh", async () => {
  mockCatalog("empty", []);
  render(<LocalModelPicker selected="removed-model" onSelect={vi.fn()} />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Refresh models" }),
    ).toBeEnabled(),
  );
  expect(screen.getByLabelText("AI model")).toHaveValue("");
  expect(
    screen.getByRole("button", { name: "Use selected model" }),
  ).toBeDisabled();
});

import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
vi.mock("./Chart", () => ({ StockChart: () => <div>Stock chart</div> }));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
describe("startup states", () => {
  it("opens imports for a fresh workplace database without fake metrics", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string) => ({
        ok: !path.endsWith("/overview"),
        status: path.endsWith("/overview") ? 404 : 200,
        json: async () =>
          path.endsWith("/overview")
            ? { error: { message: "No analysis found" } }
            : path.endsWith("/meta")
              ? { mode: "demo", ai_runtime: "ollama", weekly_jobs: false }
              : { items: [], total: 0 },
      })),
    );
    render(<App />);
    await screen.findByRole("heading", { name: "Import stock evidence" });
    expect(screen.getByLabelText("Choose inventory file")).toBeEnabled();
    expect(screen.getByText("No model selected")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("shows recoverable server errors rather than fake metrics", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ error: { message: "Startup in progress" } }),
      }),
    );
    render(<App />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Startup in progress",
      ),
    );
    expect(screen.queryByText("$59M")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });
  it("shows first-run loading state", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    render(<App />);
    expect(
      screen.getByText("Connecting to your inventory network"),
    ).toBeInTheDocument();
  });
});

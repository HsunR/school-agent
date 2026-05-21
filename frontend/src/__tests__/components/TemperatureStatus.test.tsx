import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
import { TemperatureStatus } from "@/components/TemperatureStatus";

describe("TemperatureStatus", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders CPU and GPU temperatures when API succeeds", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cpu_temp: 72.5, gpu_temp: 68.0 }),
    });

    render(<TemperatureStatus />);

    await waitFor(() => {
      expect(screen.getByText(/72.5/)).toBeDefined();
      expect(screen.getByText(/68.0/)).toBeDefined();
      expect(screen.getByText(/CPU/)).toBeDefined();
      expect(screen.getByText(/GPU/)).toBeDefined();
    });
  });

  it("shows N/A when temps are unavailable", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cpu_temp: null, gpu_temp: null }),
    });

    render(<TemperatureStatus />);

    await waitFor(() => {
      const naElements = screen.getAllByText(/N\/A/);
      expect(naElements.length).toBe(2);
    });
  });

  it("applies red text color when CPU over 85°C", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cpu_temp: 92.0, gpu_temp: 60.0 }),
    });

    render(<TemperatureStatus />);

    await waitFor(() => {
      const cpuEl = screen.getByText(/92.0/);
      expect(cpuEl.className).toContain("text-red-500");
    });
  });

  it("applies green text color when temperatures are normal", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cpu_temp: 55.0, gpu_temp: 60.0 }),
    });

    render(<TemperatureStatus />);

    await waitFor(() => {
      const cpuEl = screen.getByText(/55.0/);
      expect(cpuEl.className).toContain("text-green-500");
    });
  });
});

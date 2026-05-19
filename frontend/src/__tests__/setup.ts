import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock scrollIntoView for jsdom test environment
Element.prototype.scrollIntoView = vi.fn();

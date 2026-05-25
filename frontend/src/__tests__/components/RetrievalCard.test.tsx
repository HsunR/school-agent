import "@testing-library/jest-dom/vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";
import RetrievalCard from "@/components/RetrievalCard";

afterEach(() => {
  cleanup();
});

describe("RetrievalCard", () => {
  it("shows score for each chunk", () => {
    const chunks = [
      { preview: "宿舍管理费每学期500元", source: "学校贴吧", score: 85 },
    ];
    render(<RetrievalCard chunks={chunks} />);
    expect(screen.getByText("score: 85")).toBeInTheDocument();
  });

  it("opens a modal with original content when clicking 详情", () => {
    const chunks = [
      { preview: "宿舍管理费每学期500元", source: "学校贴吧", score: 85 },
    ];
    render(<RetrievalCard chunks={chunks} />);
    const detailButton = screen.getByText("详情 →");
    fireEvent.click(detailButton);
    expect(screen.getByText("宿舍管理费每学期500元")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows 评分中... when score is undefined", () => {
    const chunks = [
      { preview: "宿舍管理费每学期500元", source: "学校贴吧" },
    ];
    render(<RetrievalCard chunks={chunks} />);
    expect(screen.getByText("评分中...")).toBeInTheDocument();
  });
});

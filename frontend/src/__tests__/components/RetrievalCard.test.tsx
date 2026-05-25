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

describe("RetrievalCard selected chunks", () => {
  const chunks = [
    { preview: "宿舍管理费每学期500元", source: "学校贴吧", score: 90 },
    { preview: "食堂推荐窗口", source: "学校贴吧", score: 30 },
  ];

  it("renders green highlight for selected chunks", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[{ source: "学校贴吧", preview: "宿舍管理费每学期500元" }]} />);
    const labels = screen.getAllByText("✓ 已用于回答");
    expect(labels).toHaveLength(1);
  });

  it("renders no highlight when selectedChunks is empty", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[]} />);
    expect(screen.queryByText("✓ 已用于回答")).toBeNull();
  });

  it("renders no highlight when no match", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[{ source: "学校贴吧", preview: "nonexistent" }]} />);
    expect(screen.queryByText("✓ 已用于回答")).toBeNull();
  });

  it("highlights only the matching chunk", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[{ source: "学校贴吧", preview: "食堂推荐窗口" }]} />);
    const labels = screen.getAllByText("✓ 已用于回答");
    expect(labels).toHaveLength(1);
  });
});

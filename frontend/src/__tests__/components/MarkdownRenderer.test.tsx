import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import MarkdownRenderer from "@/components/MarkdownRenderer";

afterEach(() => {
  cleanup();
});

describe("MarkdownRenderer", () => {
  // 1. Plain text renders as paragraph
  it("renders plain text as a paragraph", () => {
    render(<MarkdownRenderer content="Hello world" />);
    const paragraph = screen.getByText("Hello world");
    expect(paragraph).toBeInTheDocument();
    expect(paragraph.tagName).toBe("P");
  });

  // 2. Bold text renders as <strong>
  it("renders **bold** as <strong> tag", () => {
    render(<MarkdownRenderer content="This is **bold** text" />);
    const strong = screen.getByText("bold");
    expect(strong).toBeInTheDocument();
    expect(strong.tagName).toBe("STRONG");
  });

  // 3. Italic text renders as <em>
  it("renders *italic* as <em> tag", () => {
    render(<MarkdownRenderer content="This is *italic* text" />);
    const em = screen.getByText("italic");
    expect(em).toBeInTheDocument();
    expect(em.tagName).toBe("EM");
  });

  // 4. Inline code renders as <code>
  it("renders `code` as <code> tag", () => {
    render(<MarkdownRenderer content="Use the `foo()` function" />);
    const code = screen.getByText("foo()");
    expect(code).toBeInTheDocument();
    expect(code.tagName).toBe("CODE");
  });

  // 5. Code block renders as <pre><code>
  it("renders code block with <pre> and <code>", () => {
    render(
      <MarkdownRenderer
        content={`\`\`\`
const x = 1;
console.log(x);
\`\`\``}
      />
    );
    const code = screen.getByText(/const x = 1/);
    expect(code).toBeInTheDocument();
    expect(code.tagName).toBe("CODE");
    const pre = code.closest("pre");
    expect(pre).toBeInTheDocument();
  });

  // 6. Unordered list renders as <li> tags
  it("renders list items as <li> tags", () => {
    render(
      <MarkdownRenderer
        content={`- item one
- item two
- item three`}
      />
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("item one");
    expect(items[1]).toHaveTextContent("item two");
    expect(items[2]).toHaveTextContent("item three");
  });

  // 7. Link renders as <a> tag
  it("renders [link](url) as <a> tag with href", () => {
    render(
      <MarkdownRenderer content="Click [here](https://example.com) for more" />
    );
    const link = screen.getByRole("link", { name: "here" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "https://example.com");
  });

  // 8. XSS safety: <script> tag is escaped
  it("escapes <script> tags for XSS safety", () => {
    render(
      <MarkdownRenderer content={'<script>alert("xss")</script>'} />
    );
    // The script tag content should appear as text, not execute
    expect(
      screen.getByText((content) => content.includes("alert"))
    ).toBeInTheDocument();
    // There should be no actual script elements in the DOM
    expect(document.querySelector("script")).not.toBeInTheDocument();
  });

  // 9. Mixed markdown renders correctly
  it("renders mixed markdown correctly", () => {
    const mixed = `# Heading

**Bold** and *italic* with \`inline code\`

- List item 1
- List item 2

> A blockquote`;

    render(<MarkdownRenderer content={mixed} />);
    expect(screen.getByText("Heading")).toBeInTheDocument();
    expect(screen.getByText("Bold")).toBeInTheDocument();
    expect(screen.getAllByText("italic")[0]).toBeInTheDocument();
    expect(screen.getByText("inline code")).toBeInTheDocument();
    expect(screen.getByText("List item 1")).toBeInTheDocument();
    expect(screen.getByText("List item 2")).toBeInTheDocument();
    expect(screen.getByText("A blockquote")).toBeInTheDocument();
  });

  // 10. Ordered list renders as <ol>
  it("renders ordered list items", () => {
    render(
      <MarkdownRenderer
        content={`1. first
2. second
3. third`}
      />
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("first");
    expect(items[2]).toHaveTextContent("third");
  });

  // 11. Heading renders with correct tag
  it("renders headings at the right level", () => {
    render(<MarkdownRenderer content="## Sub Heading" />);
    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent("Sub Heading");
  });

  // 12. Blockquote renders
  it("renders blockquote", () => {
    const { container } = render(
      <MarkdownRenderer content="> A notable quote" />
    );
    const blockquote = container.querySelector("blockquote");
    expect(blockquote).toBeInTheDocument();
    expect(blockquote).toHaveTextContent("A notable quote");
  });

  // 13. Inline code has Tailwind styling classes
  it("applies styling classes to inline code", () => {
    render(<MarkdownRenderer content="Use `cmd` to run" />);
    const code = screen.getByText("cmd");
    expect(code.className).toContain("bg-gray-100");
    expect(code.className).toContain("font-mono");
  });

  // 14. Code block has pre styling classes
  it("applies styling classes to code blocks", () => {
    render(
      <MarkdownRenderer
        content={`\`\`\`
const x = 1;
\`\`\``}
      />
    );
    const code = screen.getByText(/const x = 1/);
    const pre = code.closest("pre");
    expect(pre).toBeInTheDocument();
    expect(pre?.className).toContain("bg-gray-900");
    expect(pre?.className).toContain("rounded-lg");
  });

  // 15. Link has styling classes
  it("applies styling classes to links", () => {
    const { container } = render(
      <MarkdownRenderer content="[click](https://x.com)" />
    );
    const link = container.querySelector("a");
    expect(link?.className).toContain("underline");
    expect(link?.className).toContain("text-blue-600");
  });

  // 16. Image renders with constrained width
  it("renders images with constrained width", () => {
    render(<MarkdownRenderer content="![alt](https://example.com/img.png)" />);
    const img = screen.getByAltText("alt");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/img.png");
    expect(img.className).toContain("max-w-full");
  });

  // 17. Empty content renders without crashing
  it("renders empty content without crashing", () => {
    const { container } = render(<MarkdownRenderer content="" />);
    // ReactMarkdown renders nothing for empty content but should not throw
    expect(container.textContent).toBe("");
  });

  // 18. Table renders from GFM table syntax
  it("renders markdown tables with headers and cells", () => {
    const table = `| Name  | Age |
|-------|-----|
| Alice | 30  |
| Bob   | 25  |`;
    render(<MarkdownRenderer content={table} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Age")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
  });

  // 19. Horizontal rule renders
  it("renders horizontal rule from ---", () => {
    const { container } = render(<MarkdownRenderer content="---" />);
    const hr = container.querySelector("hr");
    expect(hr).toBeInTheDocument();
  });

  // 20. Strikethrough renders via GFM
  it("renders strikethrough text with ~~ ~~", () => {
    render(<MarkdownRenderer content="This is ~~strikethrough~~ text" />);
    const del = screen.getByText("strikethrough");
    expect(del).toBeInTheDocument();
    expect(del.tagName).toBe("DEL");
  });

  // 21. Multiple paragraphs separated by blank lines
  it("renders multiple paragraphs separated by blank lines", () => {
    render(
      <MarkdownRenderer
        content={"First paragraph.\n\nSecond paragraph.\n\nThird paragraph."}
      />,
    );
    const paragraphs = screen.getAllByText(/paragraph/);
    expect(paragraphs).toHaveLength(3);
  });

  // 22. Inline code inside mixed content
  it("renders inline code alongside regular text", () => {
    render(
      <MarkdownRenderer content="Run `npm install` to install dependencies" />,
    );
    const code = screen.getByText("npm install");
    expect(code).toBeInTheDocument();
    expect(code.tagName).toBe("CODE");
    expect(screen.getByText(/Run/)).toBeInTheDocument();
    expect(screen.getByText(/to install dependencies/)).toBeInTheDocument();
  });

  // 23. XSS safety: inline JavaScript event handlers are escaped
  it("escapes inline JavaScript event handlers", () => {
    render(
      <MarkdownRenderer content='<img onerror="alert(1)" src="x" />' />,
    );
    // Content should be escaped, not executed
    expect(screen.getByText((content) => content.includes("onerror"))).toBeInTheDocument();
    expect(document.querySelector("img")).not.toBeInTheDocument();
  });

  // 24. XSS safety: on* event attributes are escaped
  it("escapes on* event attributes in HTML", () => {
    render(
      <MarkdownRenderer content='<p onclick="alert(1)">click me</p>' />,
    );
    expect(screen.getByText((content) => content.includes("onclick"))).toBeInTheDocument();
    expect(document.querySelector("[onclick]")).toBeNull();
  });
});

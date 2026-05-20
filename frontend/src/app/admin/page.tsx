"use client";

import { useState, useCallback, FormEvent, useEffect, useRef, useDeferredValue } from "react";
import MarkdownRenderer from "@/components/MarkdownRenderer";

// ─── Types ───────────────────────────────────────────────────────────────────

type Category = "student_manual" | "school_forum";
type InputMode = "paste" | "file";
type ToastType = "success" | "error" | "info";

const CATEGORY_LABELS: Record<Category, string> = {
  student_manual: "学生手册",
  school_forum: "学校贴吧",
};

const CATEGORY_META: Record<
  Category,
  { bg: string; text: string; dot: string; badge: string }
> = {
  student_manual: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    dot: "bg-blue-500",
    badge: "手册",
  },
  school_forum: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    dot: "bg-orange-500",
    badge: "论坛",
  },
};

interface UploadResult {
  inserted: number;
  skipped: number;
  total: number;
}

interface StatsItem {
  category: string;
  total_count: number;
}

interface PreviewItem {
  id: string;
  document: string;
  metadata: Record<string, string>;
}

interface PreviewResponse {
  documents?: string[];
  ids?: string[];
  metadatas?: Record<string, string>[];
  total?: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const PAGE_SIZE = 20;

// ─── Icons (inline SVGs for zero dependencies) ───────────────────────────────

function IconBook() {
  return (
    <svg
      className="h-6 w-6 text-white"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
      />
    </svg>
  );
}

function IconSpinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function IconX() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function IconInfo() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function IconClose() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function IconWarning() {
  return (
    <svg
      className="h-5 w-5 text-red-600"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
      />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
      />
    </svg>
  );
}

function IconPencil() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    </svg>
  );
}

function IconFile() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

function IconEye() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
      />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

function IconChevronLeft() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
    </svg>
  );
}

function IconChevronRight() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function IconEmpty() {
  return (
    <svg className="h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
      />
    </svg>
  );
}

function IconCloudUpload() {
  return (
    <svg className="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

// ─── Page Component ──────────────────────────────────────────────────────────

export default function AdminPage() {
  // ── Form state ──
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<Category>("student_manual");
  const [showFullEditor, setShowFullEditor] = useState(false);

  const MAX_EDITOR_CHARS = 8000;
  const isContentLarge = content.length > MAX_EDITOR_CHARS;
  const deferredContent = useDeferredValue(content);
  const [delimiter, setDelimiter] = useState("-----SPILIT_BY_HSUNR-----");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  // ── Stats state ──
  const [stats, setStats] = useState<StatsItem[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  // ── Preview state ──
  const [previewData, setPreviewData] = useState<PreviewItem[]>([]);
  const [previewCategory, setPreviewCategory] = useState<Category | null>(null);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewLoading, setPreviewLoading] = useState(false);

  // ── Clear state ──
  const [clearing, setClearing] = useState(false);

  // ── File upload state ──
  const [inputMode, setInputMode] = useState<InputMode>("paste");
  const [fileName, setFileName] = useState("");
  const [fileSize, setFileSize] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Full content preservation for large-content toggle ──
  const fullContentRef = useRef("");

  // ── Toast state ──
  const [toast, setToast] = useState<{
    message: string;
    type: ToastType;
    visible: boolean;
  } | null>(null);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    setToast({ message, type, visible: false });
    // Trigger enter animation on next tick
    requestAnimationFrame(() => {
      setToast((prev) => (prev ? { ...prev, visible: true } : null));
    });
  }, []);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3500);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // ── Confirm modal state ──
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmMessage, setConfirmMessage] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  const [confirmAction, setConfirmAction] = useState<() => void>(() => {});

  // ── Preview modal state ──
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [previewShowFull, setPreviewShowFull] = useState(false);

  // ── Record delete state ──
  const [deletingRecord, setDeletingRecord] = useState(false);
  const [confirmButtonText, setConfirmButtonText] = useState("确认清空");

  // ── Load stats ──
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const res = await fetch("/api/admin/stats");
      if (res.ok) {
        const data: StatsItem[] = await res.json();
        setStats(data);
      }
    } catch {
      // ignore network errors silently
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // ── File handling ──
  const LARGE_FILE_WARN_SIZE = 500 * 1024; // 500KB

  const handleFileSelect = useCallback(
    (file: File) => {
      if (!file.name.endsWith(".txt") && !file.name.endsWith(".md")) {
        showToast("仅支持 .txt 和 .md 格式的文件", "error");
        return;
      }
      if (file.size > LARGE_FILE_WARN_SIZE) {
        showToast(
          `文件较大 (${(file.size / 1024 / 1024).toFixed(1)}MB)，` +
          "加载后仅显示前10000字符预览，完整内容将用于上传",
          "info",
        );
      }
      setFileName(file.name);
      setFileSize(file.size);
      setShowFullEditor(false);
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        fullContentRef.current = text;
        setContent(text);
      };
      reader.onerror = () => {
        showToast("文件读取失败，请重试", "error");
      };
      reader.readAsText(file);
    },
    [showToast],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect],
  );

  const handleClearFile = useCallback(() => {
    setFileName("");
    setFileSize(0);
    setContent("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // ── Upload ──
  const handleUpload = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!content.trim()) {
        showToast("请输入或上传资料内容", "error");
        return;
      }
      setUploading(true);
      setUploadResult(null);
      try {
        const res = await fetch("/api/admin/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, category, delimiter }),
        });
        if (!res.ok) {
          const err = await res.text();
          showToast(`上传失败: ${err}`, "error");
          return;
        }
        const result: UploadResult = await res.json();
        setUploadResult(result);
        showToast(
          `上传成功！新增 ${result.inserted} 条，跳过 ${result.skipped} 条`,
          "success",
        );
        loadStats();
      } catch (err) {
        showToast(`网络错误: ${err}`, "error");
      } finally {
        setUploading(false);
      }
    },
    [content, category, delimiter, loadStats, showToast],
  );

  // ── Preview ──
  const loadPreview = useCallback(
    async (cat: Category, page: number = 1) => {
      setPreviewLoading(true);
      try {
        const res = await fetch(
          `/api/admin/data?category=${cat}&page=${page}&size=${PAGE_SIZE}`,
        );
        if (res.ok) {
          const data: PreviewResponse = await res.json();
          setPreviewData(
            (data.documents || []).map((doc: string, i: number) => ({
              id: data.ids?.[i] || "",
              document: doc,
              metadata: data.metadatas?.[i] || {},
            })),
          );
          setPreviewCategory(cat);
          setPreviewPage(page);
          setPreviewTotal(data.total ?? data.documents?.length ?? 0);
        }
      } catch {
        showToast("加载预览数据失败", "error");
      } finally {
        setPreviewLoading(false);
      }
    },
    [showToast],
  );

  // ── Clear ──
  const openClearConfirm = useCallback(
    (cat: Category) => {
      setConfirmMessage(
        `确定清空「${CATEGORY_LABELS[cat]}」的所有数据吗？此操作不可恢复！`,
      );
      setConfirmButtonText("确认清空");
      const doClear = async () => {
        setClearing(true);
        try {
          const url = `/api/admin/data?category=${cat}`;
          const res = await fetch(url, { method: "DELETE" });
          if (res.ok) {
            showToast(`已清空「${CATEGORY_LABELS[cat]}」数据`, "success");
            setPreviewData([]);
            setPreviewCategory(null);
            setPreviewPage(1);
            setPreviewTotal(0);
            loadStats();
          } else {
            showToast("清空失败，请重试", "error");
          }
        } catch (err) {
          showToast(`清空失败: ${err}`, "error");
        } finally {
          setClearing(false);
          setConfirmOpen(false);
        }
      };
      setConfirmAction(() => doClear);
      setConfirmOpen(true);
    },
    [loadStats, showToast],
  );

  // ── Record Delete ──
  const handleDeleteRecord = useCallback(
    async (cat: Category, id: string) => {
      setDeletingRecord(true);
      try {
        const res = await fetch(`/api/admin/data?category=${cat}&id=${id}`, {
          method: "DELETE",
        });
        if (res.ok) {
          showToast("记录已删除", "success");
          if (previewCategory) {
            loadPreview(previewCategory, previewPage);
          }
          loadStats();
        } else {
          showToast("删除失败，请重试", "error");
        }
      } catch (err) {
        showToast(`删除失败: ${err}`, "error");
      } finally {
        setDeletingRecord(false);
        setConfirmOpen(false);
      }
    },
    [previewCategory, previewPage, loadPreview, loadStats, showToast],
  );

  const confirmDeleteRecord = useCallback(
    (cat: Category, id: string) => {
      setConfirmMessage("确定删除这条记录吗？此操作不可恢复！");
      setConfirmButtonText("确认删除");
      setConfirmAction(() => () => {
        handleDeleteRecord(cat, id);
      });
      setConfirmOpen(true);
    },
    [handleDeleteRecord],
  );

  // ── Pagination ──
  const totalPages = Math.max(1, Math.ceil(previewTotal / PAGE_SIZE));

  const goToPage = useCallback(
    (page: number) => {
      if (previewCategory) loadPreview(previewCategory, page);
    },
    [previewCategory, loadPreview],
  );

  // ── Render Helpers ──
  const toastIcon = (type: ToastType) => {
    switch (type) {
      case "success":
        return <IconCheck />;
      case "error":
        return <IconX />;
      case "info":
        return <IconInfo />;
    }
  };

  const toastColors = (type: ToastType) => {
    switch (type) {
      case "success":
        return "bg-green-50 text-green-800 border-green-200";
      case "error":
        return "bg-red-50 text-red-800 border-red-200";
      case "info":
        return "bg-blue-50 text-blue-800 border-blue-200";
    }
  };

  const toastIconColors = (type: ToastType) => {
    switch (type) {
      case "success":
        return "text-green-500";
      case "error":
        return "text-red-500";
      case "info":
        return "text-blue-500";
    }
  };

  // ── Render Pagination Numbers ──
  const renderPageNumbers = () => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1).map(
        (page) => (
          <button
            key={page}
            onClick={() => goToPage(page)}
            className={`min-w-[2rem] rounded-lg px-2 py-1 text-sm font-medium transition-colors ${
              previewPage === page
                ? "bg-blue-500 text-white shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {page}
          </button>
        ),
      );
    }

    const pages: (number | "ellipsis")[] = [];
    pages.push(1);

    if (previewPage > 3) {
      pages.push("ellipsis");
    }

    for (
      let i = Math.max(2, previewPage - 1);
      i <= Math.min(totalPages - 1, previewPage + 1);
      i++
    ) {
      pages.push(i);
    }

    if (previewPage < totalPages - 2) {
      pages.push("ellipsis");
    }

    pages.push(totalPages);

    return pages.map((item, idx) =>
      item === "ellipsis" ? (
        <span key={`e-${idx}`} className="px-1 text-gray-400 select-none">
          ...
        </span>
      ) : (
        <button
          key={item}
          onClick={() => goToPage(item)}
          className={`min-w-[2rem] rounded-lg px-2 py-1 text-sm font-medium transition-colors ${
            previewPage === item
              ? "bg-blue-500 text-white shadow-sm"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          {item}
        </button>
      ),
    );
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* ── Toast Notification ── */}
      {toast && (
        <div
          className="fixed top-4 right-4 z-50 max-w-sm"
          style={{
            transition: "opacity 0.3s ease, transform 0.3s ease",
            opacity: toast.visible ? 1 : 0,
            transform: toast.visible
              ? "translateX(0)"
              : "translateX(1.5rem)",
          }}
        >
          <div
            className={`flex items-start gap-3 rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-sm ${toastColors(toast.type)}`}
          >
            <span className={`mt-0.5 shrink-0 ${toastIconColors(toast.type)}`}>
              {toastIcon(toast.type)}
            </span>
            <p className="flex-1 text-sm font-medium leading-snug">
              {toast.message}
            </p>
            <button
              onClick={() => setToast(null)}
              className="shrink-0 rounded-lg p-0.5 text-current opacity-50 transition-opacity hover:opacity-100"
            >
              <IconClose />
            </button>
          </div>
        </div>
      )}

      {/* ── Confirm Modal ── */}
      {confirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{
            backgroundColor: "rgba(0,0,0,0.4)",
            backdropFilter: "blur(4px)",
            transition: "opacity 0.2s ease",
          }}
          onClick={() => setConfirmOpen(false)}
        >
          <div
            className="mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            style={{
              transition: "transform 0.2s ease, opacity 0.2s ease",
            }}
          >
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100">
                <IconWarning />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  确认操作
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-gray-500">
                  {confirmMessage}
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setConfirmOpen(false)}
                className="rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 hover:shadow"
              >
                取消
              </button>
              <button
                onClick={confirmAction}
                disabled={clearing || deletingRecord}
                className="inline-flex items-center gap-2 rounded-xl bg-red-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-red-600 hover:shadow disabled:cursor-not-allowed disabled:opacity-50"
              >
                {(clearing || deletingRecord) && <IconSpinner />}
                {clearing ? "清空中..." : deletingRecord ? "删除中..." : confirmButtonText}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Markdown Preview Modal ── */}
      {previewOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{
            backgroundColor: "rgba(0,0,0,0.4)",
            backdropFilter: "blur(4px)",
            transition: "opacity 0.2s ease",
          }}
          onClick={() => setPreviewOpen(false)}
        >
          <div
            className="mx-4 flex max-h-[80vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            style={{
              transition: "transform 0.2s ease, opacity 0.2s ease",
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h3 className="text-lg font-semibold text-gray-900">
                内容预览
              </h3>
              <button
                onClick={() => setPreviewOpen(false)}
                className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              >
                <IconClose />
              </button>
            </div>
            {/* Content */}
            <div className="overflow-y-auto px-6 py-4">
              <div className="prose prose-sm max-w-none text-gray-700">
                {previewShowFull || previewContent.length <= 10000 ? (
                  <MarkdownRenderer content={previewContent} />
                ) : (
                  <>
                    <MarkdownRenderer content={previewContent.slice(0, 5000) + "..."} />
                    <div className="mt-4 flex justify-center">
                      <button
                        onClick={() => setPreviewShowFull(true)}
                        className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                      >
                        显示全部内容（共 {previewContent.length} 字符）
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Main Content ── */}
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        {/* ═══ Header ═══ */}
        <header className="mb-8">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-200">
              <IconBook />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                知识库管理
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                上传、查看和管理知识库内容，支持文本粘贴和文件上传
              </p>
            </div>
          </div>
        </header>

        {/* ═══ Upload Section ═══ */}
        <section className="mb-8 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {/* Tabs */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => {
                setInputMode("paste");
                setFileName("");
              }}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors ${
                inputMode === "paste"
                  ? "border-b-2 border-blue-500 bg-white text-blue-600"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
              }`}
            >
              <IconPencil />
              粘贴文本
            </button>
            <button
              onClick={() => setInputMode("file")}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors ${
                inputMode === "file"
                  ? "border-b-2 border-blue-500 bg-white text-blue-600"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
              }`}
            >
              <IconFile />
              上传文件
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleUpload} className="space-y-5 p-5">
            {inputMode === "paste" ? (
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  资料内容
                </label>
                {isContentLarge && !showFullEditor ? (
                  <div className="space-y-3">
                    <textarea
                      value={deferredContent.slice(0, MAX_EDITOR_CHARS) + `\n\n... [内容过长，仅显示前 ${MAX_EDITOR_CHARS} 字符，共 ${content.length} 字符]`}
                      readOnly
                      rows={8}
                      className="w-full rounded-xl border border-gray-300 bg-gray-100 p-3 text-sm text-gray-500 transition-colors"
                      placeholder="粘贴或输入资料内容..."
                    />
                    <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                      <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                      <span className="flex-1">内容较大，暂只可预览前 {MAX_EDITOR_CHARS} 字符</span>
                      <button
                        type="button"
                        onClick={() => {
                          setContent(fullContentRef.current || content);
                          setShowFullEditor(true);
                        }}
                        className="shrink-0 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100"
                      >
                        加载全部内容编辑
                      </button>
                    </div>
                  </div>
                ) : (
                  <textarea
                    value={deferredContent}
                    onChange={(e) => setContent(e.target.value)}
                    rows={8}
                    className="w-full rounded-xl border border-gray-300 bg-gray-50 p-3 text-sm text-gray-900 placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
                    placeholder="粘贴或输入资料内容..."
                    required
                  />
                )}
              </div>
            ) : (
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  上传文件
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    支持 .txt 和 .md 格式
                  </span>
                </label>

                {!fileName ? (
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                    className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors ${
                      dragOver
                        ? "border-blue-400 bg-blue-50"
                        : "border-gray-300 bg-gray-50 hover:border-blue-300 hover:bg-blue-50/50"
                    }`}
                  >
                    <span
                      className={`mb-3 ${dragOver ? "text-blue-500" : "text-gray-400"}`}
                    >
                      <IconCloudUpload />
                    </span>
                    <p
                      className={`text-sm ${dragOver ? "text-blue-600" : "text-gray-500"}`}
                    >
                      {dragOver
                        ? "释放文件以上传"
                        : "拖拽文件到此处，或点击浏览"}
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      .txt 或 .md 文件
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".txt,.md"
                      className="hidden"
                      onChange={handleFileInputChange}
                    />
                  </div>
                ) : (
                  <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-gray-50 p-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-100">
                      <svg
                        className="h-5 w-5 text-blue-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900">
                        {fileName}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(fileSize)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleClearFile}
                      className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-600"
                      title="移除文件"
                    >
                      <IconClose />
                    </button>
                  </div>
                )}

                {fileName && (
                  <div className="mt-3">
                    <label className="mb-1 block text-xs font-medium text-gray-500">
                      文件内容预览（可编辑）
                    </label>
                    <textarea
                      value={deferredContent}
                      onChange={(e) => setContent(e.target.value)}
                      rows={5}
                      className="w-full rounded-xl border border-gray-300 bg-gray-50 p-3 text-sm text-gray-900 placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
                      placeholder="选择文件后将自动填充内容..."
                    />
                  </div>
                )}
              </div>
            )}

            {/* Category + Delimiter */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  资料类型
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as Category)}
                  className="w-full rounded-xl border border-gray-300 bg-white p-2.5 text-sm text-gray-900 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                >
                  <option value="student_manual">学生手册</option>
                  <option value="school_forum">学校贴吧</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  分割字符串
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    按此标记分割内容
                  </span>
                </label>
                <input
                  type="text"
                  value={delimiter}
                  onChange={(e) => setDelimiter(e.target.value)}
                  className="w-full rounded-xl border border-gray-300 bg-white p-2.5 text-sm font-mono text-gray-900 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  style={{ fontVariantLigatures: "none" }}
                />
              </div>
            </div>

            {/* Submit + Result */}
            <div className="flex flex-wrap items-center gap-4">
              <button
                type="submit"
                disabled={uploading || !content.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-500 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-blue-600 hover:shadow-md active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <IconSpinner />
                    上传中...
                  </>
                ) : (
                  <>
                    <IconUpload />
                    上传
                  </>
                )}
              </button>

              {uploadResult && (
                <div className="inline-flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
                  <IconCheck />
                  <span>
                    新增{" "}
                    <span className="font-semibold">
                      {uploadResult.inserted}
                    </span>{" "}
                    条，跳过{" "}
                    <span className="font-semibold">
                      {uploadResult.skipped}
                    </span>{" "}
                    条（共 {uploadResult.total} 段）
                  </span>
                </div>
              )}
            </div>
          </form>
        </section>

        {/* ═══ Stats Section ═══ */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            数据概览
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {(Object.keys(CATEGORY_LABELS) as Category[]).map((cat) => {
              const s = stats.find((st) => st.category === cat);
              const meta = CATEGORY_META[cat];
              return (
                <div
                  key={cat}
                  className="group rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`flex h-3 w-3 rounded-full ${meta.dot}`}
                      />
                      <span className="text-sm font-medium text-gray-700">
                        {CATEGORY_LABELS[cat]}
                      </span>
                    </div>
                    <span
                      className={`rounded-full ${meta.bg} px-2.5 py-0.5 text-xs font-medium ${meta.text}`}
                    >
                      {meta.badge}
                    </span>
                  </div>

                  <div className="mt-3 flex items-baseline">
                    {statsLoading ? (
                      <div className="h-8 w-20 animate-pulse rounded-md bg-gray-200" />
                    ) : (
                      <span className="text-3xl font-bold tracking-tight text-gray-900">
                        {s?.total_count ?? 0}
                      </span>
                    )}
                    <span className="ml-2 text-sm text-gray-400">条记录</span>
                  </div>

                  <div className="mt-4 flex items-center gap-2">
                    <button
                      onClick={() => loadPreview(cat)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
                    >
                      <IconEye />
                      预览
                    </button>
                    <button
                      onClick={() => openClearConfirm(cat)}
                      disabled={clearing}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
                    >
                      <IconTrash />
                      清空
                    </button>
                  </div>
                </div>
              );
            })}
          </div>


        </section>

        {/* ═══ Preview Section ═══ */}
        {previewCategory && (
          <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-200 px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-gray-900">
                    数据预览
                  </h2>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${CATEGORY_META[previewCategory].bg} ${CATEGORY_META[previewCategory].text}`}
                  >
                    {CATEGORY_LABELS[previewCategory]}
                  </span>
                </div>
                {previewTotal > 0 && (
                  <span className="text-sm text-gray-500">
                    共{" "}
                    <span className="font-semibold text-gray-700">
                      {previewTotal}
                    </span>{" "}
                    条记录
                  </span>
                )}
              </div>
            </div>

            {previewLoading ? (
              <div className="space-y-3 p-5">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-12 animate-pulse rounded-xl bg-gray-100"
                  />
                ))}
              </div>
            ) : previewData.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <IconEmpty />
                <p className="mt-3 text-sm text-gray-400">暂无数据</p>
                <p className="mt-1 text-xs text-gray-300">
                  请先在上方上传资料
                </p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="w-1/2 px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                          内容
                        </th>
                        <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                          Hash
                        </th>
                        <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                          时间
                        </th>
                        <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                          操作
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {previewData.map((item, i) => (
                        <tr
                          key={item.id || i}
                          className="cursor-pointer transition-colors hover:bg-blue-50/50"
                          onClick={() => {
                            setPreviewContent(item.document);
                            setPreviewShowFull(false);
                            setPreviewOpen(true);
                          }}
                        >
                          <td className="max-w-xs px-5 py-3 text-sm text-gray-700">
                            <div className="line-clamp-2 leading-relaxed">
                              {item.document?.substring(0, 200)}
                              {(item.document?.length ?? 0) > 200 ? "..." : ""}
                            </div>
                          </td>
                          <td className="whitespace-nowrap px-5 py-3">
                            <code className="rounded-md bg-gray-100 px-1.5 py-0.5 text-xs font-mono text-gray-500">
                              {item.id?.substring(0, 12)}...
                            </code>
                          </td>
                          <td className="whitespace-nowrap px-5 py-3 text-xs text-gray-500">
                            {item.metadata?.created_at
                              ? new Date(
                                  item.metadata.created_at,
                                ).toLocaleString("zh-CN")
                              : "—"}
                          </td>
                          <td className="whitespace-nowrap px-5 py-3 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                confirmDeleteRecord(
                                  previewCategory!,
                                  item.id,
                                );
                              }}
                              disabled={deletingRecord}
                              className="rounded-lg p-1.5 text-red-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                              title="删除"
                            >
                              <IconTrash />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="flex flex-col items-center justify-between gap-3 border-t border-gray-200 px-5 py-3 sm:flex-row">
                  <span className="text-sm text-gray-500">
                    第{" "}
                    {previewTotal > 0
                      ? (previewPage - 1) * PAGE_SIZE + 1
                      : 0}
                    -
                    {Math.min(previewPage * PAGE_SIZE, previewTotal)} 条，共{" "}
                    {previewTotal} 条
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => goToPage(previewPage - 1)}
                      disabled={previewPage <= 1}
                      className="rounded-lg border border-gray-300 p-1.5 text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <IconChevronLeft />
                    </button>
                    {renderPageNumbers()}
                    <button
                      onClick={() => goToPage(previewPage + 1)}
                      disabled={previewPage >= totalPages}
                      className="rounded-lg border border-gray-300 p-1.5 text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <IconChevronRight />
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        )}
      </div>
    </div>
  );
}



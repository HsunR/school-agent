"use client";

import { useState, useCallback, FormEvent, useEffect } from "react";

type Category = "student_manual" | "school_forum";

const CATEGORY_LABELS: Record<Category, string> = {
  student_manual: "学生手册",
  school_forum: "学校贴吧",
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

export default function AdminPage() {
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<Category>("student_manual");
  const [delimiter, setDelimiter] = useState("*****SPILIT_BY_HUSNR*****");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [stats, setStats] = useState<StatsItem[]>([]);
  const [previewData, setPreviewData] = useState<PreviewItem[]>([]);
  const [previewCategory, setPreviewCategory] = useState<Category | null>(null);
  const [clearing, setClearing] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch("/api/admin/stats");
      if (res.ok) setStats(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleUpload = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!content.trim()) return;
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
          alert(`Upload failed: ${err}`);
          return;
        }
        setUploadResult(await res.json());
        loadStats();
      } catch (err) {
        alert(`Network error: ${err}`);
      } finally {
        setUploading(false);
      }
    },
    [content, category, delimiter, loadStats],
  );

  const loadPreview = useCallback(async (cat: Category) => {
    try {
      const res = await fetch(`/api/admin/data?category=${cat}&page=1&size=20`);
      if (res.ok) {
        const data = await res.json();
        setPreviewData(
          (data.documents || []).map((doc: string, i: number) => ({
            id: data.ids?.[i] || "",
            document: doc,
            metadata: data.metadatas?.[i] || {},
          })),
        );
        setPreviewCategory(cat);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const handleClear = useCallback(
    async (cat?: Category) => {
      const msg = cat
        ? `确定清空「${CATEGORY_LABELS[cat]}」的所有数据吗？`
        : "确定清空所有数据吗？此操作不可恢复！";
      if (!confirm(msg)) return;
      setClearing(true);
      try {
        const url = cat ? `/api/admin/data?category=${cat}` : "/api/admin/data";
        const res = await fetch(url, { method: "DELETE" });
        if (res.ok) {
          alert("已清空");
          setPreviewData([]);
          setPreviewCategory(null);
          loadStats();
        }
      } catch (err) {
        alert(`Clear failed: ${err}`);
      } finally {
        setClearing(false);
      }
    },
    [loadStats],
  );

  return (
    <div className="mx-auto max-w-4xl p-6 space-y-8">
      <h1 className="text-2xl font-bold">知识库管理</h1>

      {/* Upload Section */}
      <section className="rounded-lg border p-4 space-y-4">
        <h2 className="text-lg font-semibold">上传资料</h2>
        <form onSubmit={handleUpload} className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">资料内容</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              className="w-full rounded border border-gray-300 p-2 text-sm"
              placeholder="粘贴或输入资料内容..."
              required
            />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">资料类型</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as Category)}
                className="w-full rounded border border-gray-300 p-2 text-sm"
              >
                <option value="student_manual">学生手册</option>
                <option value="school_forum">学校贴吧</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">分割字符串</label>
              <input
                type="text"
                value={delimiter}
                onChange={(e) => setDelimiter(e.target.value)}
                className="w-full rounded border border-gray-300 p-2 text-sm font-mono"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={uploading || !content.trim()}
            className="rounded bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {uploading ? "上传中..." : "上传"}
          </button>
        </form>
        {uploadResult && (
          <div className="rounded bg-green-50 p-3 text-sm text-green-700">
            新增 {uploadResult.inserted} 条，跳过 {uploadResult.skipped} 条
            （共 {uploadResult.total} 段）
          </div>
        )}
      </section>

      {/* Stats Section */}
      <section className="rounded-lg border p-4 space-y-4">
        <h2 className="text-lg font-semibold">数据概览</h2>
        <div className="grid grid-cols-2 gap-4">
          {(Object.keys(CATEGORY_LABELS) as Category[]).map((cat) => {
            const s = stats.find((st) => st.category === cat);
            return (
              <div key={cat} className="rounded border p-3">
                <div className="font-medium">{CATEGORY_LABELS[cat]}</div>
                <div className="mt-1 text-2xl font-bold">
                  {s?.total_count ?? "—"}
                </div>
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => loadPreview(cat)}
                    className="rounded bg-gray-100 px-2 py-1 text-xs hover:bg-gray-200"
                  >
                    预览
                  </button>
                  <button
                    onClick={() => handleClear(cat)}
                    disabled={clearing}
                    className="rounded bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100 disabled:opacity-50"
                  >
                    清空
                  </button>
                </div>
              </div>
            );
          })}
        </div>
        <button
          onClick={() => handleClear()}
          disabled={clearing}
          className="rounded bg-red-500 px-3 py-1.5 text-sm text-white hover:bg-red-600 disabled:opacity-50"
        >
          清空所有数据
        </button>
      </section>

      {/* Preview Section */}
      {previewCategory && (
        <section className="rounded-lg border p-4 space-y-4">
          <h2 className="text-lg font-semibold">
            数据预览 - {CATEGORY_LABELS[previewCategory]}
          </h2>
          {previewData.length === 0 ? (
            <p className="text-sm text-gray-500">暂无数据</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left w-1/2">内容</th>
                    <th className="px-3 py-2 text-left">Hash</th>
                    <th className="px-3 py-2 text-left">时间</th>
                  </tr>
                </thead>
                <tbody>
                  {previewData.map((item, i) => (
                    <tr key={item.id || i} className="border-b hover:bg-gray-50">
                      <td className="px-3 py-2 truncate max-w-xs">
                        {item.document?.substring(0, 120)}
                        {(item.document?.length || 0) > 120 ? "..." : ""}
                      </td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-500">
                        {item.id?.substring(0, 12)}...
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {item.metadata?.created_at
                          ? new Date(item.metadata.created_at).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

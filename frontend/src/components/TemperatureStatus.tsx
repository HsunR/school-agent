/* ── Real-time CPU/GPU temperature display ── */

"use client";

import { useState, useEffect } from "react";

interface TemperatureData {
  cpu_temp: number | null;
  gpu_temp: number | null;
}

const POLL_INTERVAL = 5000;

function tempColor(value: number | null, threshold: number): string {
  if (value === null) return "text-gray-400";
  if (value >= threshold) return "text-red-500";
  if (value >= threshold - 15) return "text-yellow-500";
  return "text-green-500";
}

export function TemperatureStatus() {
  const [data, setData] = useState<TemperatureData | null>(null);

  useEffect(() => {
    let active = true;

    const fetchTemp = async () => {
      try {
        const res = await fetch("/api/admin/temperature");
        if (!res.ok) return;
        const json: TemperatureData = await res.json();
        if (active) setData(json);
      } catch {
        // Ignore network errors
      }
    };

    fetchTemp();
    const id = setInterval(fetchTemp, POLL_INTERVAL);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const cpu = data?.cpu_temp ?? null;
  const gpu = data?.gpu_temp ?? null;

  return (
    <div className="mb-4 flex items-center gap-6 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm">
      <span className="font-medium text-gray-600">硬件温度</span>
      <div className="flex items-center gap-2">
        <span className="text-gray-400">CPU</span>
        <span className={`font-mono font-semibold ${tempColor(cpu, 85)}`}>
          {cpu !== null ? `${cpu.toFixed(1)}°C` : "N/A"}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-gray-400">GPU</span>
        <span className={`font-mono font-semibold ${tempColor(gpu, 90)}`}>
          {gpu !== null ? `${gpu.toFixed(1)}°C` : "N/A"}
        </span>
      </div>
    </div>
  );
}

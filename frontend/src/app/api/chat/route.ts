import type { NextRequest } from "next/server";

const BACKEND_URL = "http://localhost:8000/api/chat";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

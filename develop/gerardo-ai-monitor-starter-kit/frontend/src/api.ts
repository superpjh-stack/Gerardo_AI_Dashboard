let token = "";
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (init?.method && init.method !== "GET" && !token) {
    const res = await fetch("/api/v1/session");
    if (!res.ok) throw new Error("로컬 서버에 연결할 수 없습니다.");
    token = (await res.json()).token;
  }
  const response = await fetch("/api/v1" + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Local-Token": token,
      ...init?.headers,
    },
  });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("로그인이 필요합니다.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    if (response.status === 403) token = "";
    throw new Error(data?.error?.message || "요청을 처리하지 못했습니다.");
  }
  return response.json();
}

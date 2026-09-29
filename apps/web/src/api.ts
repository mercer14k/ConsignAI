let readToken = "";
let writeToken = "";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export function setCredentials(read: string, write: string) {
  readToken = read;
  writeToken = write;
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      ...(readToken ? { Authorization: `Bearer ${readToken}` } : {}),
      ...(writeToken ? { "X-API-Key": writeToken } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.error?.message || `Request failed (${response.status})`,
      response.status,
    );
  }
  return response.json();
}
export const money = (cents: number, compact = false) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    ...(compact ? { notation: "compact" as const } : {}),
  }).format(cents / 100);
export const number = (n: number) => new Intl.NumberFormat("en-US").format(n);
export const label = (s: string) => s.replaceAll("_", " ");
export async function exportCsv(params: URLSearchParams) {
  const response = await fetch(`/api/v1/export/exceptions.csv?${params}`, {
    headers: readToken ? { Authorization: `Bearer ${readToken}` } : {},
  });
  if (!response.ok) throw new Error("Export failed");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = "consignai-exceptions.csv";
  a.click();
  URL.revokeObjectURL(url);
}

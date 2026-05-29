const BASE = "http://127.0.0.1:8000";

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Category = "vuln" | "logic";
export type JobState = "queued" | "running" | "done" | "error";

export interface Finding {
  severity: Severity;
  category: Category;
  source: "static" | "llm";
  file: string;
  line: number | null;
  title: string;
  detail: string;
  confidence: "high" | "medium" | "low";
}

export interface ScanResult {
  repo: string;
  head: string;
  findings: Finding[];
  files_scanned: number;
  files_skipped: number;
  truncated: boolean;
  notes: string[];
}

export interface Job {
  id: string;
  state: JobState;
  progress: string;
  git_url: string;
  created_at: string;
  result: ScanResult | null;
  error: string | null;
}

export async function startScan(
  git_url: string,
  github_token?: string
): Promise<Job> {
  const res = await fetch(`${BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      git_url,
      github_token: github_token || null,
    }),
  });
  if (!res.ok) throw new Error(`Scan failed: ${res.status}`);
  return res.json();
}

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`${BASE}/scan/${id}`);
  if (!res.ok) throw new Error(`Status failed: ${res.status}`);
  return res.json();
}

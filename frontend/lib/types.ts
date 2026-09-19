export type WorkflowStatus =
  | "PENDING"
  | "PLANNING"
  | "RUNNING"
  | "AWAITING_APPROVAL"
  | "SUCCEEDED"
  | "FAILED";

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface WorkflowSummary {
  id: string;
  status: WorkflowStatus;
  user_request: string;
  role: string;
  current_step_index: number;
  step_count: number;
  created_at: string;
  updated_at: string;
}

export interface PlanStep {
  step_index: number;
  tool_name: string;
  arguments: Record<string, JsonValue>;
  description?: string;
}

export interface ApprovalRecord {
  id?: string;
  requested_at?: string;
  decided_at?: string | null;
  decided_by?: string | null;
  decision?: "APPROVED" | "REJECTED" | null;
  reason?: string | null;
}

export interface Workflow {
  id: string;
  status: WorkflowStatus;
  user_request: string;
  role: string;
  current_step_index: number;
  plan: PlanStep[];
  results: Record<string, JsonValue>;
  errors: Record<string, JsonValue>;
  risk_levels: Record<string, string>;
  verifications: Record<string, JsonValue>;
  approved_steps: number[];
  approvals: Record<string, ApprovalRecord>;
  final_result: JsonValue;
  created_at: string;
  updated_at: string;
}

export interface BenchmarkResult {
  mode: "stack" | "synthetic";
  scenario: "approval_path" | "denied_path" | "read_path";
  concurrency: 1 | 5 | 10 | 25;
  n: number;
  success_rate: number;
  mean_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  throughput_ops_s: number;
}

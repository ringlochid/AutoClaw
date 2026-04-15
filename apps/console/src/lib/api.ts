export type TaskSummary = {
  id: string;
  title: string;
  status: string;
};

export type FlowSummary = {
  id: string;
  task: TaskSummary;
  status: string;
  execution_no: number;
  seed_compiled_plan_id: string;
  active_flow_revision_id: string | null;
  node_count: number;
  done_node_count: number;
  blocked_node_count: number;
  pending_approval_count: number;
  projected_manifest_count: number;
  latest_checkpoint_status: string | null;
  latest_checkpoint_summary: string | null;
  latest_checkpoint_wait_reason: string | null;
};

export type FlowOperatorNode = {
  id: string;
  node_key: string;
  node_path: string;
  state: string;
  order_index: number;
  current_attempt: {
    id: string;
    number: number;
    status: string;
    retry_of_node_attempt_id: string | null;
    failure_signature: string | null;
  } | null;
  current_session: {
    id: string;
    status: string;
    last_seen_at: string | null;
    ended_at: string | null;
  } | null;
  current_manifest: {
    id: string;
    flow_id: string;
    flow_node_id: string;
    node_attempt_id: string;
    manifest_no: number;
    status: string;
    projected_at: string;
    acked_at: string | null;
  } | null;
  current_wait_reason: string | null;
  retryable: boolean;
};

export type FlowOperatorApproval = {
  id: string;
  flow_id: string;
  node_attempt_id: string | null;
  flow_node_id: string | null;
  status: string;
  reason: string;
};

export type FlowOperator = {
  flow: {
    id: string;
    task_id: string;
    status: string;
    execution_no: number;
    seed_compiled_plan_id: string;
    active_flow_revision_id: string | null;
    node_count: number;
    nodes: FlowOperatorNode[];
  };
  task: TaskSummary;
  pending_approval_count: number;
  projected_manifest_count: number;
  approvals: FlowOperatorApproval[];
};

export type ApprovalResolutionStatus = 'approved' | 'rejected' | 'not_required';

const API_BASE = import.meta.env.VITE_AUTOCLAW_API_BASE_URL ?? 'http://127.0.0.1:8001';
const API_KEY = import.meta.env.VITE_AUTOCLAW_API_KEY;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_KEY) {
    throw new Error('Missing VITE_AUTOCLAW_API_KEY for console API access');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'X-AutoClaw-API-Key': API_KEY,
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function fetchFlows(): Promise<FlowSummary[]> {
  return request<FlowSummary[]>('/flows');
}

export async function fetchFlowOperator(flowId: string): Promise<FlowOperator> {
  return request<FlowOperator>(`/flows/${flowId}/operator`);
}

export async function continueFlow(flowId: string): Promise<void> {
  await request(`/flows/${flowId}/continue`, { method: 'POST' });
}

export async function pauseFlow(flowId: string): Promise<void> {
  await request(`/flows/${flowId}/pause`, { method: 'POST' });
}

export async function cancelFlow(flowId: string): Promise<void> {
  await request(`/flows/${flowId}/cancel`, { method: 'POST' });
}

export async function retryFlowNode(flowId: string, flowNodeId: string): Promise<void> {
  await request(`/flows/${flowId}/nodes/${flowNodeId}/retry`, { method: 'POST' });
}

export async function resolveApproval(
  approvalId: string,
  status: ApprovalResolutionStatus,
): Promise<void> {
  await request(`/approvals/${approvalId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({
      status,
      resolution_payload: { source: 'console-operator' },
    }),
  });
}

export async function requestReplan(
  flowId: string,
  payload: {
    requesting_flow_node_id: string;
    requesting_node_attempt_id: string;
    reason: string;
    patch: {
      nodes: { id: string; role: string; mode: string; policy?: string | null }[];
      edges: { from: string; to: string; when?: string | null; kind?: string }[];
    };
  },
): Promise<void> {
  await request(`/flows/${flowId}/replans`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

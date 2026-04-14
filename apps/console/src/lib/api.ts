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

export type FlowOperator = {
  flow: {
    id: string;
    task_id: string;
    status: string;
    execution_no: number;
    seed_compiled_plan_id: string;
    active_flow_revision_id: string | null;
    node_count: number;
    nodes: {
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
        provider_session_key: string;
        status: string;
      } | null;
      current_manifest: {
        id: string;
        status: string;
        manifest_no: number;
      } | null;
    }[];
  };
  task: {
    id: string;
    title: string;
    description: string | null;
    status: string;
    input_payload: Record<string, unknown>;
  };
  revisions: {
    id: string;
    revision_no: number;
    compiled_plan_id: string;
    workflow_version_id: string;
    parent_flow_revision_id: string | null;
    status: string;
    reason: string | null;
    adopted_at: string | null;
  }[];
  replans: {
    id: string;
    status: string;
    reason: string;
    candidate_flow_revision_id: string | null;
  }[];
  attempts: {
    id: string;
    flow_node_id: string;
    flow_node_key: string;
    flow_node_path: string;
    number: number;
    status: string;
    started_at: string;
    finished_at: string | null;
  }[];
  approvals: {
    id: string;
    status: string;
    reason: string;
    flow_node_id: string | null;
    node_attempt_id: string | null;
  }[];
  checkpoints: {
    id: string;
    flow_node_id: string;
    node_attempt_id: string;
    sequence_no: number;
    status: string;
    summary: string;
    wait_reason: string | null;
  }[];
  sessions: {
    id: string;
    flow_node_id: string;
    provider_session_key: string;
    status: string;
    last_seen_at: string | null;
  }[];
  manifests: {
    id: string;
    flow_node_id: string;
    node_attempt_id: string;
    status: string;
    manifest_no: number;
    acked_at: string | null;
  }[];
  context_items: {
    id: string;
    title: string;
    scope: string;
    kind: string;
    status: string;
    published_by: string;
  }[];
};

const API_BASE = import.meta.env.VITE_AUTOCLAW_API_BASE_URL ?? 'http://127.0.0.1:8001';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
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

export async function runWatchdog(flowId: string): Promise<void> {
  await request(`/flows/${flowId}/watchdog`, { method: 'POST' });
}

export async function requestReplan(
  flowId: string,
  payload: {
    requesting_flow_node_id: string;
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

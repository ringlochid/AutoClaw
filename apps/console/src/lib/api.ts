export type ConsoleRuntimeConfig = {
  apiBaseUrl: string;
  apiKey: string | null;
  refreshIntervalMs: number;
  supportsAuthoring: boolean;
};

export type WorkspaceRoot = {
  id: string;
  scope: string;
  key: string;
  title: string;
  storage_uri: string;
  kind: string;
  mode: string;
  status: string;
  content_hash: string;
  metadata: Record<string, unknown>;
};

export type ContextSpace = {
  id: string;
  scope: string;
  key: string;
  title: string;
  storage_uri: string;
  source_workspace_root_id: string | null;
  status: string;
  content_hash: string;
  metadata: Record<string, unknown>;
};

export type ManifestRoot = {
  id: string;
  task_id: string;
  key: string;
  storage_uri: string;
  status: string;
  metadata: Record<string, unknown>;
};

export type TaskResourceBinding = {
  id: string;
  task_id: string;
  binding_role: string;
  workspace_root_id: string | null;
  context_space_id: string | null;
  manifest_root_id: string | null;
  mode: string;
  read_only: boolean | null;
  required: boolean;
  metadata: Record<string, unknown>;
  workspace_root: WorkspaceRoot | null;
  context_space: ContextSpace | null;
  manifest_root: ManifestRoot | null;
};

export type TaskSummary = {
  id: string;
  title: string;
  status: string;
};

export type TaskDetail = TaskSummary & {
  description: string | null;
  input_payload: Record<string, unknown>;
  resource_bindings: TaskResourceBinding[];
};

export type ContextManifestSummary = {
  id: string;
  flow_id: string;
  flow_node_id: string;
  node_attempt_id: string;
  node_session_id: string | null;
  manifest_no: number;
  manifest_payload: Record<string, unknown>;
  manifest_root_id: string | null;
  status: string;
  projected_at: string;
  acked_at: string | null;
};

export type FlowOperatorNode = {
  id: string;
  node_key: string;
  node_path: string;
  state: string;
  order_index: number;
  status_payload: Record<string, unknown>;
  effective_payload: Record<string, unknown>;
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
  current_manifest: ContextManifestSummary | null;
  current_wait_reason: string | null;
  retryable: boolean;
};

export type FlowOperatorEdge = {
  from_node_key: string;
  to_node_key: string;
  edge_kind: string;
  condition_expr: string | null;
  order_index: number;
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
    compiled_plan_id: string | null;
    workflow_version_id: string | null;
    node_count: number;
    nodes: FlowOperatorNode[];
    edges: FlowOperatorEdge[];
  };
  task: TaskDetail;
  pending_approval_count: number;
  projected_manifest_count: number;
  approvals: FlowOperatorApproval[];
};

export type ApprovalResolutionStatus = 'approved' | 'rejected' | 'not_required';
export type RegistryKind = 'workflows' | 'roles' | 'policies';

export type RegistryDefinitionSummary = {
  key: string;
  description: string | null;
  latest_version: number | null;
  latest_status: string | null;
  published_version: number | null;
  draft_version: number | null;
  updated_at: string | null;
};

export type RegistryDefinitionVersionDetail = {
  id: string;
  key: string;
  version: number;
  status: string;
  description: string | null;
  content: Record<string, unknown>;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RegistrySkillSummary = {
  provider: string;
  key: string;
  source_uri: string | null;
  description: string | null;
  published_version: string | null;
};

export type WorkflowValidationResult = {
  valid: boolean;
  normalized_plan: Record<string, unknown>;
};

const ENV_API_BASE = (import.meta.env.VITE_AUTOCLAW_API_BASE_URL as string | undefined) ?? '';
const ENV_API_KEY = (import.meta.env.VITE_AUTOCLAW_API_KEY as string | undefined) ?? '';
const DEFAULT_RUNTIME_CONFIG: ConsoleRuntimeConfig = {
  apiBaseUrl: ENV_API_BASE,
  apiKey: ENV_API_KEY || null,
  refreshIntervalMs: 5000,
  supportsAuthoring: true,
};

let runtimeConfigPromise: Promise<ConsoleRuntimeConfig> | null = null;

function joinApiPath(baseUrl: string, path: string): string {
  if (!baseUrl) {
    return path;
  }
  return `${baseUrl.replace(/\/$/, '')}${path}`;
}

export async function fetchConsoleRuntimeConfig(force = false): Promise<ConsoleRuntimeConfig> {
  if (!force && runtimeConfigPromise) {
    return runtimeConfigPromise;
  }

  runtimeConfigPromise = (async () => {
    const configUrl = joinApiPath(ENV_API_BASE, '/console/config');
    try {
      const response = await fetch(configUrl, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`${response.status}: ${await response.text()}`);
      }
      const payload = (await response.json()) as Partial<ConsoleRuntimeConfig>;
      return {
        apiBaseUrl: payload.apiBaseUrl ?? DEFAULT_RUNTIME_CONFIG.apiBaseUrl,
        apiKey: payload.apiKey ?? DEFAULT_RUNTIME_CONFIG.apiKey,
        refreshIntervalMs: payload.refreshIntervalMs ?? DEFAULT_RUNTIME_CONFIG.refreshIntervalMs,
        supportsAuthoring: payload.supportsAuthoring ?? DEFAULT_RUNTIME_CONFIG.supportsAuthoring,
      };
    } catch (error) {
      if (DEFAULT_RUNTIME_CONFIG.apiKey || DEFAULT_RUNTIME_CONFIG.apiBaseUrl) {
        return DEFAULT_RUNTIME_CONFIG;
      }
      throw new Error(
        error instanceof Error
          ? `Unable to load console runtime config: ${error.message}`
          : 'Unable to load console runtime config',
      );
    }
  })();

  return runtimeConfigPromise;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const runtimeConfig = await fetchConsoleRuntimeConfig();
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has('Content-Type') && init?.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  if (runtimeConfig.apiKey) {
    headers.set('X-AutoClaw-API-Key', runtimeConfig.apiKey);
  }

  const response = await fetch(joinApiPath(runtimeConfig.apiBaseUrl, path), {
    ...init,
    headers,
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
      description?: string | null;
      policy?: string | null;
      defaults?: Record<string, unknown>;
      task_defaults?: Record<string, unknown>;
      nodes: {
        id: string;
        role: string;
        mode: string;
        policy?: string | null;
        description?: string | null;
        metadata?: Record<string, unknown>;
        resources?: Record<string, unknown>;
        skill_refs?: Record<string, unknown>[];
      }[];
      edges: { from: string; to: string; when?: string | null; kind?: string }[];
      skill_bindings?: Record<string, unknown>[];
      skill_refs?: Record<string, unknown>[];
    };
  },
): Promise<void> {
  await request(`/flows/${flowId}/replans`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchRegistrySummaries(
  kind: RegistryKind,
): Promise<RegistryDefinitionSummary[]> {
  return request<RegistryDefinitionSummary[]>(`/registry/${kind}`);
}

export async function fetchRegistryVersions(
  kind: RegistryKind,
  key: string,
): Promise<RegistryDefinitionVersionDetail[]> {
  return request<RegistryDefinitionVersionDetail[]>(`/registry/${kind}/${key}/versions`);
}

export async function putRegistryDraft(
  kind: RegistryKind,
  key: string,
  seed: Record<string, unknown>,
): Promise<RegistryDefinitionVersionDetail> {
  return request<RegistryDefinitionVersionDetail>(`/registry/${kind}/${key}/draft`, {
    method: 'PUT',
    body: JSON.stringify(seed),
  });
}

export async function publishRegistryVersion(
  kind: RegistryKind,
  key: string,
  versionNumber: number,
): Promise<RegistryDefinitionVersionDetail> {
  return request<RegistryDefinitionVersionDetail>(
    `/registry/${kind}/${key}/versions/${versionNumber}/publish`,
    { method: 'POST' },
  );
}

export async function validateWorkflowSeed(
  seed: Record<string, unknown>,
): Promise<WorkflowValidationResult> {
  return request<WorkflowValidationResult>('/registry/workflows/validate', {
    method: 'POST',
    body: JSON.stringify(seed),
  });
}

export async function fetchRegistrySkills(): Promise<RegistrySkillSummary[]> {
  return request<RegistrySkillSummary[]>('/registry/skills');
}

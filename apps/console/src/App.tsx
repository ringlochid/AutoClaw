import { useEffect, useMemo, useState } from 'react';
import {
  cancelFlow,
  continueFlow,
  fetchConsoleRuntimeConfig,
  fetchFlowOperator,
  fetchFlows,
  fetchRegistrySkills,
  fetchRegistrySummaries,
  fetchRegistryVersions,
  pauseFlow,
  publishRegistryVersion,
  putRegistryDraft,
  requestReplan,
  resolveApproval,
  retryFlowNode,
  validateWorkflowSeed,
  type ApprovalResolutionStatus,
  type ConsoleRuntimeConfig,
  type FlowOperator,
  type FlowOperatorEdge,
  type FlowOperatorNode,
  type FlowSummary,
  type RegistryDefinitionSummary,
  type RegistryDefinitionVersionDetail,
  type RegistryKind,
  type RegistrySkillSummary,
  type WorkflowValidationResult,
} from './lib/api';

const REGISTRY_KINDS: RegistryKind[] = ['workflows', 'roles', 'policies'];

type ConsoleView = 'operator' | 'registry';

type JsonRecord = Record<string, unknown>;

function replanEligibleNodes(flow: FlowOperator | null): FlowOperatorNode[] {
  if (!flow) {
    return [];
  }

  return flow.flow.nodes.filter(
    (node) => node.current_attempt !== null && node.current_attempt.status !== 'running',
  );
}

function defaultReplanRequesterId(flow: FlowOperator | null): string | null {
  return replanEligibleNodes(flow)[0]?.id ?? null;
}

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as JsonRecord;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === 'string');
}

function asRecordArray(value: unknown): JsonRecord[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is JsonRecord => item !== null);
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function kindLabel(kind: RegistryKind): string {
  return kind[0].toUpperCase() + kind.slice(1, kind.length - 1);
}

function defaultRegistryDraft(kind: RegistryKind): string {
  if (kind === 'roles') {
    return prettyJson({
      id: 'new-role',
      kind: 'worker',
      description: 'Role description',
      allowed_modes: ['persistent_execute'],
      default_policy: 'default',
      checkpoint_schema: 'worker_result_v1',
      defaults: {},
      skill_refs: [],
    });
  }

  if (kind === 'policies') {
    return prettyJson({
      id: 'new-policy',
      description: 'Policy description',
      rules: {},
    });
  }

  return prettyJson({
    id: 'new-workflow',
    description: 'Workflow description',
    defaults: { metadata: {}, skill_refs: [] },
    nodes: [
      {
        id: 'root',
        role: 'planner-supervisor',
        mode: 'plan',
        description: 'Plan the work',
        metadata: {},
        skill_refs: [],
      },
    ],
    edges: [],
    skill_refs: [],
  });
}

function nodeTitle(node: FlowOperatorNode): string {
  return node.node_path || node.node_key;
}

function operatorNodeBadges(node: FlowOperatorNode, edges: FlowOperatorEdge[]): string[] {
  const badges: string[] = [];
  if (node.current_attempt) {
    badges.push(`attempt #${node.current_attempt.number}`);
  }
  if (node.current_wait_reason) {
    badges.push(`wait ${node.current_wait_reason}`);
  }
  if (node.retryable) {
    badges.push('retry-ready');
  }
  const outgoing = edges.filter((edge) => edge.from_node_key === node.node_key).length;
  if (outgoing > 0) {
    badges.push(`${outgoing} outgoing`);
  }
  return badges;
}

function App() {
  const [view, setView] = useState<ConsoleView>('operator');
  const [runtimeConfig, setRuntimeConfig] = useState<ConsoleRuntimeConfig | null>(null);
  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [selectedFlowId, setSelectedFlowId] = useState<string | null>(null);
  const [selectedFlow, setSelectedFlow] = useState<FlowOperator | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedReplanNodeId, setSelectedReplanNodeId] = useState<string | null>(null);
  const [replanJson, setReplanJson] = useState(`{
  "reason": "operator requested hierarchy-safe replan",
  "patch": {
    "description": "Runtime replan",
    "nodes": [
      { "id": "root", "role": "planner-supervisor", "mode": "plan", "description": "Replan root" },
      { "id": "root.discovery", "role": "main-loop-worker", "mode": "persistent_execute", "metadata": { "lane": "discovery" } },
      { "id": "root.review", "role": "reviewer", "mode": "review" },
      { "id": "root.sync", "role": "syncer", "mode": "sync" }
    ],
    "edges": [
      { "from": "root", "to": "root.discovery" },
      { "from": "root.discovery", "to": "root.review" },
      { "from": "root.review", "to": "root.sync" }
    ]
  }
}`);
  const [loadingFlows, setLoadingFlows] = useState(false);
  const [loadingRegistry, setLoadingRegistry] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [registryKind, setRegistryKind] = useState<RegistryKind>('workflows');
  const [registrySummaries, setRegistrySummaries] = useState<RegistryDefinitionSummary[]>([]);
  const [selectedRegistryKey, setSelectedRegistryKey] = useState<string | null>(null);
  const [registryVersions, setRegistryVersions] = useState<RegistryDefinitionVersionDetail[]>([]);
  const [registryEditorJson, setRegistryEditorJson] = useState(defaultRegistryDraft('workflows'));
  const [registrySkills, setRegistrySkills] = useState<RegistrySkillSummary[]>([]);
  const [registryValidation, setRegistryValidation] = useState<WorkflowValidationResult | null>(null);

  async function refreshFlows(preferredFlowId?: string | null) {
    setLoadingFlows(true);
    setError(null);
    try {
      const nextFlows = await fetchFlows();
      setFlows(nextFlows);
      const nextSelectedFlowId = preferredFlowId ?? selectedFlowId ?? nextFlows[0]?.id ?? null;
      setSelectedFlowId(nextSelectedFlowId);
      if (!nextSelectedFlowId) {
        setSelectedFlow(null);
        setSelectedNodeId(null);
        setSelectedReplanNodeId(null);
        return;
      }

      const nextFlow = await fetchFlowOperator(nextSelectedFlowId);
      setSelectedFlow(nextFlow);
      const eligibleNodes = replanEligibleNodes(nextFlow);
      setSelectedReplanNodeId((current) =>
        current && eligibleNodes.some((node) => node.id === current)
          ? current
          : defaultReplanRequesterId(nextFlow),
      );
      setSelectedNodeId((current) =>
        current && nextFlow.flow.nodes.some((node) => node.id === current)
          ? current
          : nextFlow.flow.nodes[0]?.id ?? null,
      );
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unknown error');
    } finally {
      setLoadingFlows(false);
    }
  }

  async function selectFlow(flowId: string) {
    setSelectedFlowId(flowId);
    setLoadingFlows(true);
    setError(null);
    try {
      const nextFlow = await fetchFlowOperator(flowId);
      setSelectedFlow(nextFlow);
      setSelectedNodeId(nextFlow.flow.nodes[0]?.id ?? null);
      setSelectedReplanNodeId(defaultReplanRequesterId(nextFlow));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unknown error');
    } finally {
      setLoadingFlows(false);
    }
  }

  async function runAction(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError(null);
    try {
      await fn();
      await refreshFlows(selectedFlowId);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unknown error');
    } finally {
      setBusy(null);
    }
  }

  async function loadRegistryKinds(
    kind: RegistryKind,
    preferredKey?: string | null,
    preserveEditor = true,
  ) {
    setLoadingRegistry(true);
    setError(null);
    try {
      const [nextSummaries, nextSkills] = await Promise.all([
        fetchRegistrySummaries(kind),
        kind === 'workflows' ? fetchRegistrySkills() : Promise.resolve([]),
      ]);
      setRegistrySummaries(nextSummaries);
      setRegistrySkills(nextSkills);

      const nextKey = preferredKey ?? selectedRegistryKey ?? nextSummaries[0]?.key ?? null;
      setSelectedRegistryKey(nextKey);

      if (!nextKey) {
        setRegistryVersions([]);
        setRegistryValidation(null);
        if (!preserveEditor) {
          setRegistryEditorJson(defaultRegistryDraft(kind));
        }
        return;
      }

      const nextVersions = await fetchRegistryVersions(kind, nextKey);
      setRegistryVersions(nextVersions);
      if (!preserveEditor || !selectedRegistryKey || selectedRegistryKey !== nextKey) {
        setRegistryEditorJson(prettyJson(nextVersions[0]?.content ?? defaultRegistryDraft(kind)));
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unknown error');
    } finally {
      setLoadingRegistry(false);
    }
  }

  async function selectRegistryKey(key: string) {
    setSelectedRegistryKey(key);
    setLoadingRegistry(true);
    setError(null);
    try {
      const nextVersions = await fetchRegistryVersions(registryKind, key);
      setRegistryVersions(nextVersions);
      setRegistryEditorJson(prettyJson(nextVersions[0]?.content ?? defaultRegistryDraft(registryKind)));
      setRegistryValidation(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unknown error');
    } finally {
      setLoadingRegistry(false);
    }
  }

  async function validateRegistryDraftAction() {
    try {
      const parsed = JSON.parse(registryEditorJson) as JsonRecord;
      const validation = await validateWorkflowSeed(parsed);
      setRegistryValidation(validation);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Invalid workflow draft JSON');
    }
  }

  async function saveRegistryDraftAction() {
    setBusy('save-draft');
    setError(null);
    try {
      const parsed = JSON.parse(registryEditorJson) as JsonRecord;
      const key = asString(parsed.id);
      if (!key) {
        throw new Error('Draft JSON must include a string id');
      }
      const saved = await putRegistryDraft(registryKind, key, parsed);
      setRegistryValidation(null);
      await loadRegistryKinds(registryKind, key, false);
      setRegistryEditorJson(prettyJson(saved.content));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to save draft');
    } finally {
      setBusy(null);
    }
  }

  async function publishRegistryVersionAction(versionNumber: number) {
    if (!selectedRegistryKey) {
      return;
    }

    setBusy(`publish-${versionNumber}`);
    setError(null);
    try {
      await publishRegistryVersion(registryKind, selectedRegistryKey, versionNumber);
      await loadRegistryKinds(registryKind, selectedRegistryKey, true);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to publish version');
    } finally {
      setBusy(null);
    }
  }

  async function submitReplan() {
    if (!selectedFlow) {
      return;
    }

    const requester = replanEligibleNodes(selectedFlow).find(
      (node) => node.id === selectedReplanNodeId,
    );
    const requesterAttempt = requester?.current_attempt;
    if (!requester || !requesterAttempt) {
      setError('Choose a requester node that already has a non-running attempt boundary.');
      return;
    }

    try {
      const parsed = JSON.parse(replanJson) as {
        reason: string;
        patch: {
          description?: string | null;
          policy?: string | null;
          defaults?: Record<string, unknown>;
          nodes: {
            id: string;
            role: string;
            mode: string;
            policy?: string | null;
            description?: string | null;
            metadata?: Record<string, unknown>;
            skill_refs?: Record<string, unknown>[];
          }[];
          edges: { from: string; to: string; when?: string | null; kind?: string }[];
          skill_bindings?: Record<string, unknown>[];
          skill_refs?: Record<string, unknown>[];
        };
      };
      await runAction('replan', () =>
        requestReplan(selectedFlow.flow.id, {
          requesting_flow_node_id: requester.id,
          requesting_node_attempt_id: requesterAttempt.id,
          reason: parsed.reason,
          patch: parsed.patch,
        }),
      );
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Invalid replan payload');
    }
  }

  useEffect(() => {
    void (async () => {
      try {
        setRuntimeConfig(await fetchConsoleRuntimeConfig());
      } catch (nextError) {
        setError(nextError instanceof Error ? nextError.message : 'Unknown error');
      }
    })();
    void refreshFlows();
    void loadRegistryKinds('workflows', null, false);
  }, []);

  const availableReplanNodes = useMemo(
    () => replanEligibleNodes(selectedFlow),
    [selectedFlow],
  );

  const selectedReplanNode = useMemo(() => {
    if (!selectedFlow || !selectedReplanNodeId) {
      return null;
    }
    return selectedFlow.flow.nodes.find((node) => node.id === selectedReplanNodeId) ?? null;
  }, [selectedFlow, selectedReplanNodeId]);

  const retryableNodes = useMemo(
    () => (selectedFlow?.flow.nodes ?? []).filter((node) => node.retryable),
    [selectedFlow],
  );

  const selectedNode = useMemo(() => {
    if (!selectedFlow || !selectedNodeId) {
      return null;
    }
    return selectedFlow.flow.nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [selectedFlow, selectedNodeId]);

  const selectedNodeEffectivePayload = useMemo(
    () => asRecord(selectedNode?.effective_payload ?? null),
    [selectedNode],
  );

  const selectedNodeDescriptionContext = useMemo(
    () => asRecord(selectedNodeEffectivePayload?.description_context),
    [selectedNodeEffectivePayload],
  );

  const selectedNodeProvenance = useMemo(
    () => asRecord(selectedNodeEffectivePayload?.provenance),
    [selectedNodeEffectivePayload],
  );

  const selectedNodeSkillBindings = useMemo(() => {
    const skillBindings = selectedNodeEffectivePayload?.skill_bindings;
    return Array.isArray(skillBindings) ? skillBindings : [];
  }, [selectedNodeEffectivePayload]);

  const selectedNodeIncomingEdges = useMemo(() => {
    if (!selectedFlow || !selectedNode) {
      return [];
    }
    return selectedFlow.flow.edges.filter((edge) => edge.to_node_key === selectedNode.node_key);
  }, [selectedFlow, selectedNode]);

  const selectedNodeOutgoingEdges = useMemo(() => {
    if (!selectedFlow || !selectedNode) {
      return [];
    }
    return selectedFlow.flow.edges.filter((edge) => edge.from_node_key === selectedNode.node_key);
  }, [selectedFlow, selectedNode]);

  const selectedRegistrySummary = useMemo(
    () => registrySummaries.find((summary) => summary.key === selectedRegistryKey) ?? null,
    [registrySummaries, selectedRegistryKey],
  );

  const registryDraft = useMemo(() => {
    try {
      return JSON.parse(registryEditorJson) as JsonRecord;
    } catch {
      return null;
    }
  }, [registryEditorJson]);

  const registryEditorKey = useMemo(
    () => asString(registryDraft?.id),
    [registryDraft],
  );

  const registryDraftWorkflowNodes = useMemo(
    () => asRecordArray(registryDraft?.nodes),
    [registryDraft],
  );

  const registryDraftWorkflowEdges = useMemo(
    () => asRecordArray(registryDraft?.edges),
    [registryDraft],
  );

  const registryDraftWorkflowSkillRefs = useMemo(
    () => [
      ...asRecordArray(asRecord(registryDraft?.defaults)?.skill_refs),
      ...asRecordArray(registryDraft?.skill_refs),
    ],
    [registryDraft],
  );

  async function resolvePendingApproval(
    approvalId: string,
    status: ApprovalResolutionStatus,
  ) {
    await runAction(`approval-${approvalId}-${status}`, () => resolveApproval(approvalId, status));
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>AutoClaw Console</h1>
        <p>Graph-native runtime inspection, control, and draft authoring.</p>

        <div className="mode-switch">
          <button
            type="button"
            className={view === 'operator' ? 'active' : ''}
            onClick={() => setView('operator')}
          >
            Operator
          </button>
          <button
            type="button"
            className={view === 'registry' ? 'active' : ''}
            onClick={() => setView('registry')}
          >
            Registry
          </button>
        </div>

        {runtimeConfig ? (
          <div className="small subtle-block">
            Runtime config loaded from server. Authoring {runtimeConfig.supportsAuthoring ? 'enabled' : 'disabled'}.
          </div>
        ) : null}

        {view === 'operator' ? (
          <>
            <button
              type="button"
              onClick={() => void refreshFlows(selectedFlowId)}
              disabled={loadingFlows || !!busy}
            >
              {loadingFlows ? 'Refreshing…' : 'Refresh flows'}
            </button>
            <div className="flow-list" style={{ marginTop: '1rem' }}>
              {flows.map((flow) => (
                <button
                  key={flow.id}
                  type="button"
                  className={`flow-card ${selectedFlowId === flow.id ? 'active' : ''}`}
                  onClick={() => void selectFlow(flow.id)}
                >
                  <h2>{flow.task.title}</h2>
                  <div className="meta">Flow {flow.id.slice(0, 8)} · {flow.status}</div>
                  <div className="small">Nodes {flow.done_node_count}/{flow.node_count} done</div>
                  <div className="small">
                    approvals {flow.pending_approval_count} · manifests {flow.projected_manifest_count}
                  </div>
                  {flow.latest_checkpoint_summary ? (
                    <div className="small">Last: {flow.latest_checkpoint_summary}</div>
                  ) : null}
                </button>
              ))}
              {!flows.length && <div className="empty">No flows yet.</div>}
            </div>
          </>
        ) : (
          <>
            <div className="mode-switch compact">
              {REGISTRY_KINDS.map((kind) => (
                <button
                  key={kind}
                  type="button"
                  className={registryKind === kind ? 'active' : ''}
                  onClick={() => {
                    setRegistryKind(kind);
                    setSelectedRegistryKey(null);
                    setRegistryVersions([]);
                    setRegistryValidation(null);
                    setRegistryEditorJson(defaultRegistryDraft(kind));
                    void loadRegistryKinds(kind, null, false);
                  }}
                >
                  {kindLabel(kind)}
                </button>
              ))}
            </div>

            <div className="toolbar stacked">
              <button
                type="button"
                onClick={() => void loadRegistryKinds(registryKind, selectedRegistryKey, true)}
                disabled={loadingRegistry || !!busy}
              >
                {loadingRegistry ? 'Refreshing…' : `Refresh ${kindLabel(registryKind)}`}
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedRegistryKey(null);
                  setRegistryVersions([]);
                  setRegistryValidation(null);
                  setRegistryEditorJson(defaultRegistryDraft(registryKind));
                }}
              >
                New draft template
              </button>
            </div>

            <div className="flow-list" style={{ marginTop: '1rem' }}>
              {registrySummaries.map((summary) => (
                <button
                  key={summary.key}
                  type="button"
                  className={`flow-card ${selectedRegistryKey === summary.key ? 'active' : ''}`}
                  onClick={() => void selectRegistryKey(summary.key)}
                >
                  <h2>{summary.key}</h2>
                  {summary.description ? <div className="small">{summary.description}</div> : null}
                  <div className="small">
                    latest {summary.latest_version ?? '—'} · published {summary.published_version ?? '—'}
                  </div>
                  <div className="small">draft {summary.draft_version ?? '—'}</div>
                </button>
              ))}
              {!registrySummaries.length && <div className="empty">No definitions loaded.</div>}
            </div>
          </>
        )}
      </aside>

      <main className="content">
        {error ? <p className="error">{error}</p> : null}

        {view === 'operator' ? (
          !selectedFlow ? (
            <div className="empty">Pick a flow to inspect it.</div>
          ) : (
            <>
              <div className="toolbar">
                <button
                  type="button"
                  onClick={() => void runAction('continue', () => continueFlow(selectedFlow.flow.id))}
                  disabled={!!busy}
                >
                  {busy === 'continue' ? 'Continuing…' : 'Continue'}
                </button>
                <button
                  type="button"
                  onClick={() => void runAction('pause', () => pauseFlow(selectedFlow.flow.id))}
                  disabled={!!busy}
                >
                  {busy === 'pause' ? 'Pausing…' : 'Pause'}
                </button>
                <button
                  type="button"
                  onClick={() => void runAction('cancel', () => cancelFlow(selectedFlow.flow.id))}
                  disabled={!!busy}
                >
                  {busy === 'cancel' ? 'Cancelling…' : 'Cancel'}
                </button>
                <button
                  type="button"
                  onClick={() => void refreshFlows(selectedFlow.flow.id)}
                  disabled={loadingFlows || !!busy}
                >
                  {loadingFlows ? 'Refreshing…' : 'Refresh current flow'}
                </button>
              </div>

              <div className="panel-grid">
                <section className="panel">
                  <h3>Overview</h3>
                  <div className="kv">Task: {selectedFlow.task.title}</div>
                  <div className="kv">Task status: {selectedFlow.task.status}</div>
                  <div className="kv">Flow status: {selectedFlow.flow.status}</div>
                  <div className="kv">Flow id: {selectedFlow.flow.id}</div>
                  <div className="kv">Active revision: {selectedFlow.flow.active_flow_revision_id ?? '—'}</div>
                  <div className="kv">Compiled plan: {selectedFlow.flow.compiled_plan_id ?? '—'}</div>
                  <div className="kv">Workflow version: {selectedFlow.flow.workflow_version_id ?? '—'}</div>
                  <div className="kv">Seed compiled plan: {selectedFlow.flow.seed_compiled_plan_id}</div>
                  <div className="kv">Pending approvals: {selectedFlow.pending_approval_count}</div>
                  <div className="kv">Projected manifests: {selectedFlow.projected_manifest_count}</div>
                </section>

                <section className="panel panel-span-2">
                  <h3>Runtime graph</h3>
                  <p className="small">
                    Nodes are ordered from the active flow revision. Click a node to inspect its purpose,
                    provenance, and live runtime overlays.
                  </p>
                  <div className="graph-grid">
                    {selectedFlow.flow.nodes.map((node) => {
                      const outgoingEdges = selectedFlow.flow.edges.filter(
                        (edge) => edge.from_node_key === node.node_key,
                      );
                      return (
                        <button
                          key={node.id}
                          type="button"
                          className={`node-card ${selectedNodeId === node.id ? 'selected' : ''}`}
                          onClick={() => setSelectedNodeId(node.id)}
                        >
                          <div className="node-card-topline">
                            <span className="badge">{node.state}</span>
                            <span className="small">#{node.order_index}</span>
                          </div>
                          <strong>{nodeTitle(node)}</strong>
                          {node.current_attempt ? (
                            <div className="small">
                              attempt {node.current_attempt.number} · {node.current_attempt.status}
                            </div>
                          ) : (
                            <div className="small">No attempt yet</div>
                          )}
                          <div className="pill-row">
                            {operatorNodeBadges(node, selectedFlow.flow.edges).map((badge) => (
                              <span key={badge} className="edge-chip">{badge}</span>
                            ))}
                          </div>
                          {outgoingEdges.length ? (
                            <div className="small edge-list-inline">
                              {outgoingEdges.map((edge) => (
                                <span key={`${edge.from_node_key}-${edge.to_node_key}-${edge.order_index}`}>
                                  → {edge.to_node_key}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                </section>

                <section className="panel panel-span-2">
                  <h3>Node detail</h3>
                  {!selectedNode ? (
                    <div className="small">Pick a node from the graph.</div>
                  ) : (
                    <div className="detail-grid">
                      <div>
                        <div className="kv">Node: {selectedNode.node_path}</div>
                        <div className="kv">State: {selectedNode.state}</div>
                        <div className="kv">Role: {asString(asRecord(selectedNodeEffectivePayload?.role)?.key) ?? '—'}</div>
                        <div className="kv">Policy: {asString(asRecord(selectedNodeEffectivePayload?.policy)?.key) ?? '—'}</div>
                        <div className="kv">Mode: {asString(selectedNodeEffectivePayload?.mode) ?? '—'}</div>
                        <div className="kv">
                          Description: {asString(selectedNodeEffectivePayload?.description) ?? '—'}
                        </div>
                        <div className="kv">
                          Wait reason: {selectedNode.current_wait_reason ?? '—'}
                        </div>
                      </div>

                      <div>
                        <div className="kv">Workflow description</div>
                        <div className="small detail-text">
                          {asString(selectedNodeDescriptionContext?.workflow) ?? '—'}
                        </div>
                        <div className="kv">Role description</div>
                        <div className="small detail-text">
                          {asString(selectedNodeDescriptionContext?.role) ?? '—'}
                        </div>
                        <div className="kv">Policy description</div>
                        <div className="small detail-text">
                          {asString(selectedNodeDescriptionContext?.policy) ?? '—'}
                        </div>
                      </div>

                      <div>
                        <div className="kv">Current attempt</div>
                        <div className="small detail-text">
                          {selectedNode.current_attempt
                            ? `#${selectedNode.current_attempt.number} · ${selectedNode.current_attempt.status}`
                            : 'No attempt yet'}
                        </div>
                        <div className="kv">Current session</div>
                        <div className="small detail-text">
                          {selectedNode.current_session
                            ? `${selectedNode.current_session.status} · last seen ${formatDate(selectedNode.current_session.last_seen_at)}`
                            : 'No active session'}
                        </div>
                        <div className="kv">Current manifest</div>
                        <div className="small detail-text">
                          {selectedNode.current_manifest
                            ? `manifest #${selectedNode.current_manifest.manifest_no} · ${selectedNode.current_manifest.status}`
                            : 'No projected manifest'}
                        </div>
                      </div>

                      <div>
                        <div className="kv">Incoming edges</div>
                        <div className="small detail-text">
                          {selectedNodeIncomingEdges.length
                            ? selectedNodeIncomingEdges
                                .map((edge) => `${edge.from_node_key} → ${edge.to_node_key}`)
                                .join(', ')
                            : 'None'}
                        </div>
                        <div className="kv">Outgoing edges</div>
                        <div className="small detail-text">
                          {selectedNodeOutgoingEdges.length
                            ? selectedNodeOutgoingEdges
                                .map((edge) => `${edge.from_node_key} → ${edge.to_node_key}`)
                                .join(', ')
                            : 'None'}
                        </div>
                      </div>

                      <div className="detail-section full-width">
                        <div className="kv">Metadata</div>
                        <pre>{prettyJson(selectedNodeEffectivePayload?.metadata ?? {})}</pre>
                      </div>

                      <div className="detail-section full-width">
                        <div className="kv">Skill bindings</div>
                        <pre>{prettyJson(selectedNodeSkillBindings)}</pre>
                      </div>

                      <div className="detail-section full-width">
                        <div className="kv">Provenance</div>
                        <pre>{prettyJson(selectedNodeProvenance ?? {})}</pre>
                      </div>
                    </div>
                  )}
                </section>

                <section className="panel">
                  <h3>Retryable nodes</h3>
                  {retryableNodes.length ? (
                    <ul>
                      {retryableNodes.map((node) => (
                        <li key={node.id}>
                          <button
                            type="button"
                            disabled={!!busy}
                            onClick={() =>
                              void runAction(`retry-${node.id}`, () =>
                                retryFlowNode(selectedFlow.flow.id, node.id),
                              )
                            }
                          >
                            {busy === `retry-${node.id}` ? 'Retrying…' : `Retry ${node.node_path}`}
                          </button>
                          {node.current_wait_reason ? ` · ${node.current_wait_reason}` : ''}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="small">Only nodes with an explicit retry boundary are shown here.</div>
                  )}
                </section>

                <section className="panel">
                  <h3>Pending approvals</h3>
                  {selectedFlow.approvals.length ? (
                    <ul>
                      {selectedFlow.approvals.map((approval) => (
                        <li key={approval.id}>
                          <span className="badge">{approval.status}</span>
                          {approval.reason}
                          <div className="approval-actions">
                            <button
                              type="button"
                              disabled={!!busy}
                              onClick={() => void resolvePendingApproval(approval.id, 'approved')}
                            >
                              {busy === `approval-${approval.id}-approved` ? 'Approving…' : 'Approve'}
                            </button>
                            <button
                              type="button"
                              disabled={!!busy}
                              onClick={() => void resolvePendingApproval(approval.id, 'rejected')}
                            >
                              {busy === `approval-${approval.id}-rejected` ? 'Rejecting…' : 'Reject'}
                            </button>
                            <button
                              type="button"
                              disabled={!!busy}
                              onClick={() => void resolvePendingApproval(approval.id, 'not_required')}
                            >
                              {busy === `approval-${approval.id}-not_required`
                                ? 'Updating…'
                                : 'Not required'}
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="small">No pending approvals.</div>
                  )}
                </section>

                <section className="panel panel-span-2">
                  <h3>Request replan</h3>
                  <p className="small">
                    Choose a completed or blocked attempt boundary, then submit a replacement graph.
                  </p>
                  {availableReplanNodes.length ? (
                    <>
                      <label className="small" htmlFor="replan-requester">
                        Requesting node
                      </label>
                      <select
                        id="replan-requester"
                        value={selectedReplanNodeId ?? ''}
                        onChange={(event) => setSelectedReplanNodeId(event.target.value || null)}
                        style={{ width: '100%', marginTop: '0.35rem', marginBottom: '0.5rem' }}
                      >
                        {availableReplanNodes.map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.node_path} · attempt #{node.current_attempt?.number} ({node.current_attempt?.status})
                          </option>
                        ))}
                      </select>
                      <div className="small" style={{ marginBottom: '0.75rem' }}>
                        {selectedReplanNode?.current_attempt
                          ? `Replan provenance will bind to attempt #${selectedReplanNode.current_attempt.number}.`
                          : 'Choose a requester node with a real attempt boundary.'}
                      </div>
                    </>
                  ) : (
                    <div className="small" style={{ marginBottom: '0.75rem' }}>
                      No non-running requester attempt is available yet.
                    </div>
                  )}
                  <textarea
                    className="json-editor"
                    value={replanJson}
                    onChange={(event) => setReplanJson(event.target.value)}
                    rows={14}
                  />
                  <div style={{ marginTop: '0.75rem' }}>
                    <button
                      type="button"
                      onClick={() => void submitReplan()}
                      disabled={!!busy || !selectedReplanNode?.current_attempt}
                    >
                      {busy === 'replan' ? 'Submitting replan…' : 'Submit replan'}
                    </button>
                  </div>
                </section>
              </div>
            </>
          )
        ) : (
          <div className="panel-grid">
            <section className="panel">
              <h3>{kindLabel(registryKind)} summary</h3>
              <div className="kv">Selected key: {selectedRegistryKey ?? registryEditorKey ?? 'new draft'}</div>
              <div className="kv">Draft version: {selectedRegistrySummary?.draft_version ?? '—'}</div>
              <div className="kv">Published version: {selectedRegistrySummary?.published_version ?? '—'}</div>
              <div className="kv">Latest status: {selectedRegistrySummary?.latest_status ?? '—'}</div>
              <div className="kv">Updated at: {formatDate(selectedRegistrySummary?.updated_at)}</div>
              {registryKind === 'workflows' ? (
                <div className="small subtle-block">
                  Validation runs through the compiler-backed workflow contract before publish.
                </div>
              ) : null}
            </section>

            <section className="panel panel-span-2">
              <h3>{kindLabel(registryKind)} draft editor</h3>
              <div className="toolbar">
                {registryKind === 'workflows' ? (
                  <button
                    type="button"
                    onClick={() => void validateRegistryDraftAction()}
                    disabled={!!busy}
                  >
                    Validate draft
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => void saveRegistryDraftAction()}
                  disabled={!!busy}
                >
                  {busy === 'save-draft' ? 'Saving…' : 'Save draft'}
                </button>
              </div>
              <div className="small" style={{ marginBottom: '0.5rem' }}>
                Draft key resolves from the JSON <code>id</code> field.
              </div>
              <textarea
                className="json-editor"
                value={registryEditorJson}
                onChange={(event) => setRegistryEditorJson(event.target.value)}
                rows={24}
              />
              {registryValidation ? (
                <div className="detail-section" style={{ marginTop: '1rem' }}>
                  <div className="kv">Validation result</div>
                  <pre>{prettyJson(registryValidation.normalized_plan)}</pre>
                </div>
              ) : null}
            </section>

            <section className="panel">
              <h3>Version history</h3>
              {registryVersions.length ? (
                <ul>
                  {registryVersions.map((version) => (
                    <li key={version.id}>
                      <div className="small">
                        v{version.version} · {version.status} · {formatDate(version.updated_at)}
                      </div>
                      <div className="approval-actions" style={{ marginTop: '0.5rem' }}>
                        <button
                          type="button"
                          onClick={() => setRegistryEditorJson(prettyJson(version.content))}
                        >
                          Load into editor
                        </button>
                        <button
                          type="button"
                          disabled={!!busy || version.status === 'published'}
                          onClick={() => void publishRegistryVersionAction(version.version)}
                        >
                          {busy === `publish-${version.version}`
                            ? 'Publishing…'
                            : version.status === 'published'
                              ? 'Published'
                              : 'Publish'}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="small">No versions loaded yet.</div>
              )}
            </section>

            {registryKind === 'workflows' ? (
              <>
                <section className="panel panel-span-2">
                  <h3>Draft graph preview</h3>
                  {registryDraftWorkflowNodes.length ? (
                    <div className="graph-grid">
                      {registryDraftWorkflowNodes.map((node) => {
                        const nodeId = asString(node.id) ?? 'unknown';
                        const outgoingEdges = registryDraftWorkflowEdges.filter(
                          (edge) => asString(edge.from) === nodeId,
                        );
                        const nodeSkillRefs = asRecordArray(node.skill_refs);
                        return (
                          <div key={nodeId} className="node-card static">
                            <div className="node-card-topline">
                              <span className="badge">{asString(node.mode) ?? 'unknown'}</span>
                              <span className="small">{asString(node.role) ?? '—'}</span>
                            </div>
                            <strong>{nodeId}</strong>
                            {asString(node.description) ? (
                              <div className="small detail-text">{asString(node.description)}</div>
                            ) : null}
                            <div className="pill-row">
                              {nodeSkillRefs.map((skillRef) => {
                                const provider = asString(skillRef.provider) ?? 'skill';
                                const key = asString(skillRef.key) ?? 'unknown';
                                return (
                                  <span key={`${provider}:${key}`} className="edge-chip">
                                    {provider}:{key}
                                  </span>
                                );
                              })}
                            </div>
                            {outgoingEdges.length ? (
                              <div className="small edge-list-inline">
                                {outgoingEdges.map((edge, index) => (
                                  <span key={`${nodeId}-${index}`}>
                                    → {asString(edge.to) ?? 'unknown'}
                                  </span>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="small">Add workflow nodes in the draft JSON to preview the authoring graph.</div>
                  )}
                </section>

                <section className="panel panel-span-2">
                  <h3>Workflow-level skill refs</h3>
                  {registryDraftWorkflowSkillRefs.length ? (
                    <div className="pill-row">
                      {registryDraftWorkflowSkillRefs.map((skillRef, index) => {
                        const provider = asString(skillRef.provider) ?? 'skill';
                        const key = asString(skillRef.key) ?? `ref-${index}`;
                        const state = asString(skillRef.state);
                        return (
                          <span key={`${provider}:${key}:${index}`} className="edge-chip">
                            {provider}:{key}{state ? ` (${state})` : ''}
                          </span>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="small">No workflow-level skill refs in the current draft.</div>
                  )}
                </section>

                <section className="panel panel-span-2">
                  <h3>Published skills</h3>
                  {registrySkills.length ? (
                    <div className="graph-grid compact-grid">
                      {registrySkills.map((skill) => (
                        <div key={`${skill.provider}:${skill.key}`} className="node-card static">
                          <strong>{skill.provider}:{skill.key}</strong>
                          <div className="small">version {skill.published_version ?? '—'}</div>
                          {skill.description ? <div className="small detail-text">{skill.description}</div> : null}
                          {skill.source_uri ? <div className="small detail-text">{skill.source_uri}</div> : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="small">No published skills in the registry yet.</div>
                  )}
                </section>
              </>
            ) : null}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

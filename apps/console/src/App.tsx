import { useEffect, useMemo, useState } from 'react';
import {
  cancelFlow,
  continueFlow,
  fetchFlowOperator,
  fetchFlows,
  pauseFlow,
  requestReplan,
  resolveApproval,
  retryFlowNode,
  type ApprovalResolutionStatus,
  type FlowOperator,
  type FlowOperatorNode,
  type FlowSummary,
} from './lib/api';

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

function App() {
  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [selectedFlowId, setSelectedFlowId] = useState<string | null>(null);
  const [selectedFlow, setSelectedFlow] = useState<FlowOperator | null>(null);
  const [selectedReplanNodeId, setSelectedReplanNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [replanJson, setReplanJson] = useState(`{
  "reason": "operator requested hierarchy-safe replan",
  "patch": {
    "nodes": [
      { "id": "root", "role": "planner-supervisor", "mode": "plan" },
      { "id": "root.discovery", "role": "main-loop-worker", "mode": "persistent_execute" },
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

  async function refreshFlows(preferredFlowId?: string | null) {
    setLoading(true);
    setError(null);
    try {
      const nextFlows = await fetchFlows();
      setFlows(nextFlows);
      const nextSelected = preferredFlowId ?? selectedFlowId ?? nextFlows[0]?.id ?? null;
      setSelectedFlowId(nextSelected);
      if (nextSelected) {
        const nextFlow = await fetchFlowOperator(nextSelected);
        const eligibleNodes = replanEligibleNodes(nextFlow);
        setSelectedFlow(nextFlow);
        setSelectedReplanNodeId((current) =>
          current && eligibleNodes.some((node) => node.id === current)
            ? current
            : defaultReplanRequesterId(nextFlow),
        );
      } else {
        setSelectedFlow(null);
        setSelectedReplanNodeId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshFlows();
  }, []);

  async function selectFlow(flowId: string) {
    setSelectedFlowId(flowId);
    setLoading(true);
    setError(null);
    try {
      const nextFlow = await fetchFlowOperator(flowId);
      setSelectedFlow(nextFlow);
      setSelectedReplanNodeId(defaultReplanRequesterId(nextFlow));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  async function runAction(label: string, fn: () => Promise<void>) {
    if (!selectedFlowId) return;
    setBusy(label);
    setError(null);
    try {
      await fn();
      await refreshFlows(selectedFlowId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBusy(null);
    }
  }

  const availableReplanNodes = useMemo(
    () => replanEligibleNodes(selectedFlow),
    [selectedFlow],
  );

  const selectedReplanNode: FlowOperatorNode | null = useMemo(() => {
    if (!selectedFlow || !selectedReplanNodeId) {
      return null;
    }
    return selectedFlow.flow.nodes.find((node) => node.id === selectedReplanNodeId) ?? null;
  }, [selectedFlow, selectedReplanNodeId]);

  async function submitReplan() {
    if (!selectedFlow) return;

    const requester = availableReplanNodes.find((node) => node.id === selectedReplanNodeId);
    const requesterAttempt = requester?.current_attempt;
    if (!requester || !requesterAttempt) {
      setError('Choose a requester node that already has a non-running attempt boundary.');
      return;
    }

    try {
      const parsed = JSON.parse(replanJson) as {
        reason: string;
        patch: {
          nodes: { id: string; role: string; mode: string; policy?: string | null }[];
          edges: { from: string; to: string; when?: string | null; kind?: string }[];
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid replan payload');
    }
  }

  const retryableNodes = useMemo(
    () => (selectedFlow?.flow.nodes ?? []).filter((node) => node.retryable),
    [selectedFlow],
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
        <p>Operator surface for flow control and summary inspection.</p>
        <button onClick={() => void refreshFlows(selectedFlowId)} disabled={loading || !!busy}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
        <div className="flow-list" style={{ marginTop: '1rem' }}>
          {flows.map((flow) => (
            <button
              key={flow.id}
              className={`flow-card ${selectedFlowId === flow.id ? 'active' : ''}`}
              onClick={() => void selectFlow(flow.id)}
              type="button"
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
      </aside>
      <main className="content">
        {error ? <p className="error">{error}</p> : null}
        {!selectedFlow ? (
          <div className="empty">Pick a flow to inspect it.</div>
        ) : (
          <>
            <div className="toolbar">
              <button
                onClick={() => void runAction('continue', () => continueFlow(selectedFlow.flow.id))}
                disabled={!!busy}
              >
                {busy === 'continue' ? 'Continuing…' : 'Continue'}
              </button>
              <button
                onClick={() => void runAction('pause', () => pauseFlow(selectedFlow.flow.id))}
                disabled={!!busy}
              >
                {busy === 'pause' ? 'Pausing…' : 'Pause'}
              </button>
              <button
                onClick={() => void runAction('cancel', () => cancelFlow(selectedFlow.flow.id))}
                disabled={!!busy}
              >
                {busy === 'cancel' ? 'Cancelling…' : 'Cancel'}
              </button>
            </div>
            <div className="panel-grid">
              <section className="panel">
                <h3>Overview</h3>
                <div className="kv">Task: {selectedFlow.task.title}</div>
                <div className="kv">Task status: {selectedFlow.task.status}</div>
                <div className="kv">Flow status: {selectedFlow.flow.status}</div>
                <div className="kv">
                  Active revision: {selectedFlow.flow.active_flow_revision_id ?? '—'}
                </div>
                <div className="kv">Seed compiled plan: {selectedFlow.flow.seed_compiled_plan_id}</div>
                <div className="kv">Pending approvals: {selectedFlow.pending_approval_count}</div>
                <div className="kv">Projected manifests: {selectedFlow.projected_manifest_count}</div>
              </section>

              <section className="panel">
                <h3>Nodes</h3>
                <ul>
                  {selectedFlow.flow.nodes.map((node) => (
                    <li key={node.id}>
                      <span className="badge">{node.state}</span>
                      <strong>{node.node_path}</strong>
                      {node.current_attempt
                        ? ` · attempt ${node.current_attempt.number} (${node.current_attempt.status})`
                        : ''}
                      {node.current_manifest ? ` · manifest ${node.current_manifest.status}` : ''}
                      {node.current_wait_reason ? ` · wait ${node.current_wait_reason}` : ''}
                      {node.retryable ? ' · retry-ready' : ''}
                    </li>
                  ))}
                </ul>
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
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
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

              <section className="panel">
                <h3>Request replan</h3>
                <p className="small">Choose a completed or blocked attempt boundary, then submit a replacement graph.</p>
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
                  value={replanJson}
                  onChange={(event) => setReplanJson(event.target.value)}
                  rows={16}
                  style={{
                    width: '100%',
                    background: '#0a1224',
                    color: '#dfe7f8',
                    border: '1px solid #22304d',
                    borderRadius: 8,
                    padding: '0.75rem',
                  }}
                />
                <div style={{ marginTop: '0.75rem' }}>
                  <button
                    onClick={() => void submitReplan()}
                    disabled={!!busy || !selectedReplanNode?.current_attempt}
                  >
                    {busy === 'replan' ? 'Submitting replan…' : 'Submit replan'}
                  </button>
                </div>
              </section>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;

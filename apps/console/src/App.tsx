import { useEffect, useMemo, useState } from 'react';
import {
  cancelFlow,
  continueFlow,
  fetchFlowOperator,
  fetchFlows,
  pauseFlow,
  retryFlowNode,
  requestReplan,
  runWatchdog,
  type FlowOperator,
  type FlowSummary,
} from './lib/api';

function App() {
  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [selectedFlowId, setSelectedFlowId] = useState<string | null>(null);
  const [selectedFlow, setSelectedFlow] = useState<FlowOperator | null>(null);
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
        setSelectedFlow(await fetchFlowOperator(nextSelected));
      } else {
        setSelectedFlow(null);
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
      setSelectedFlow(await fetchFlowOperator(flowId));
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

  async function submitReplan() {
    if (!selectedFlow) return;
    const requester = selectedFlow.flow.nodes[0];
    if (!requester) {
      setError('No active flow node available for replan request.');
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
          reason: parsed.reason,
          patch: parsed.patch,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid replan payload');
    }
  }

  const retryableNodes = useMemo(
    () =>
      (selectedFlow?.flow.nodes ?? []).filter((node) =>
        ['waiting', 'paused', 'failed'].includes(node.state),
      ),
    [selectedFlow],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>AutoClaw Console</h1>
        <p>Flow-first operator view for the fresh runtime.</p>
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
              <button
                onClick={() => void runAction('watchdog', () => runWatchdog(selectedFlow.flow.id))}
                disabled={!!busy}
              >
                {busy === 'watchdog' ? 'Running watchdog…' : 'Watchdog'}
              </button>
            </div>
            <div className="panel-grid">
              <section className="panel">
                <h3>Overview</h3>
                <div className="kv">Task: {selectedFlow.task.title}</div>
                <div className="kv">Task status: {selectedFlow.task.status}</div>
                <div className="kv">Flow status: {selectedFlow.flow.status}</div>
                <div className="kv">Active revision: {selectedFlow.flow.active_flow_revision_id ?? '—'}</div>
                <div className="kv">Seed compiled plan: {selectedFlow.flow.seed_compiled_plan_id}</div>
                <pre>{JSON.stringify(selectedFlow.task.input_payload, null, 2)}</pre>
              </section>

              <section className="panel">
                <h3>Nodes</h3>
                <ul>
                  {selectedFlow.flow.nodes.map((node) => (
                    <li key={node.id}>
                      <span className="badge">{node.state}</span>
                      <strong>{node.node_path}</strong>
                      {node.current_attempt ? ` · attempt ${node.current_attempt.number} (${node.current_attempt.status})` : ''}
                      {node.current_manifest ? ` · manifest ${node.current_manifest.status}` : ''}
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
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="small">No retryable nodes right now.</div>
                )}
              </section>

              <section className="panel">
                <h3>Revisions + replans</h3>
                <ul>
                  {selectedFlow.revisions.map((revision) => (
                    <li key={revision.id}>
                      <span className="badge">{revision.status}</span>
                      rev {revision.revision_no} · workflow version {revision.workflow_version_id.slice(0, 8)}
                    </li>
                  ))}
                </ul>
                <ul>
                  {selectedFlow.replans.map((replan) => (
                    <li key={replan.id}>
                      <span className="badge">{replan.status}</span>
                      {replan.reason}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3>Attempts</h3>
                <ul>
                  {selectedFlow.attempts.map((attempt) => (
                    <li key={attempt.id}>
                      <span className="badge">{attempt.status}</span>
                      {attempt.flow_node_path} · #{attempt.number}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3>Approvals</h3>
                <ul>
                  {selectedFlow.approvals.map((approval) => (
                    <li key={approval.id}>
                      <span className="badge">{approval.status}</span>
                      {approval.reason}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3>Checkpoints</h3>
                <ul>
                  {selectedFlow.checkpoints.map((checkpoint) => (
                    <li key={checkpoint.id}>
                      <span className="badge">{checkpoint.status}</span>
                      {checkpoint.summary}
                      {checkpoint.wait_reason ? ` · wait=${checkpoint.wait_reason}` : ''}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3>Sessions + manifests</h3>
                <ul>
                  {selectedFlow.sessions.map((session) => (
                    <li key={session.id}>
                      <span className="badge">{session.status}</span>
                      {session.provider_session_key}
                    </li>
                  ))}
                </ul>
                <ul>
                  {selectedFlow.manifests.map((manifest) => (
                    <li key={manifest.id}>
                      <span className="badge">{manifest.status}</span>
                      manifest #{manifest.manifest_no}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3>Context items</h3>
                <ul>
                  {selectedFlow.context_items.map((item) => (
                    <li key={item.id}>
                      <span className="badge">{item.status}</span>
                      {item.title} · {item.scope} · {item.kind}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h3>Request replan</h3>
                <p className="small">Submit a replacement graph against the active flow.</p>
                <textarea
                  value={replanJson}
                  onChange={(event) => setReplanJson(event.target.value)}
                  rows={16}
                  style={{ width: '100%', background: '#0a1224', color: '#dfe7f8', border: '1px solid #22304d', borderRadius: 8, padding: '0.75rem' }}
                />
                <div style={{ marginTop: '0.75rem' }}>
                  <button onClick={() => void submitReplan()} disabled={!!busy}>
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

from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class DefinitionVersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SkillProvider(StrEnum):
    OPENCLAW = "openclaw"
    LOCAL = "local"
    REMOTE = "remote"


class SkillBindingState(StrEnum):
    ALLOWED = "allowed"
    PREFERRED = "preferred"
    REQUIRED = "required"
    BLOCKED = "blocked"


class WorkflowMode(StrEnum):
    PLAN = "plan"
    PERSISTENT_EXECUTE = "persistent_execute"
    REVIEW = "review"
    WAIT = "wait"
    PAUSE = "pause"
    SYNC = "sync"


class FlowEdgeKind(StrEnum):
    CONTROL = "control"
    DEPENDENCY = "dependency"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"


class FlowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    PAUSED = "paused"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"


class FlowRevisionStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    RETIRED = "retired"
    ABORTED = "aborted"


class FlowNodeState(StrEnum):
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class NodeAttemptStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    ABORTED = "aborted"


class CheckpointStatus(StrEnum):
    GREEN = "green"
    RETRY = "retry"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"


class WaitReason(StrEnum):
    APPROVAL = "approval"
    DEPENDENCY = "dependency"
    WATCHDOG = "watchdog"
    OPERATOR = "operator"
    CONTEXT = "context"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class NodePlanRevisionStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ADOPTED = "adopted"
    SUPERSEDED = "superseded"


class NodeSessionStatus(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    ENDED = "ended"


class ContextItemScope(StrEnum):
    TASK_SHARED = "task_shared"
    FLOW_SHARED = "flow_shared"
    NODE_PRIVATE = "node_private"
    ATTEMPT_SCRATCH = "attempt_scratch"


class ContextItemKind(StrEnum):
    FACT = "fact"
    DECISION = "decision"
    SUMMARY = "summary"
    SUGGESTION = "suggestion"
    NOTE = "note"
    ARTIFACT = "artifact"
    LOG = "log"


class ContextItemStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ContextManifestStatus(StrEnum):
    PROJECTED = "projected"
    ACKED = "acked"
    SUPERSEDED = "superseded"

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


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"


class AttemptStatus(StrEnum):
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
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"


class FlowNodeState(StrEnum):
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class CheckpointStatus(StrEnum):
    GREEN = "green"
    RETRY = "retry"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

"""Internal typed backend/control-plane clients."""

from cyber_agent_test_core.backend.auth import (
    AuthenticationProvider,
    RefreshingTokenProvider,
    SecretResolver,
)
from cyber_agent_test_core.backend.client import HTTPBackendClient
from cyber_agent_test_core.backend.contracts import (
    AgentRegistrationAPI,
    AgentStatusAPI,
    BackendClient,
    FeatureFlagsAPI,
    PackageMetadataAPI,
    PolicyAPI,
)
from cyber_agent_test_core.backend.exceptions import (
    BackendAuthenticationError,
    BackendConnectionError,
    BackendError,
    BackendHTTPError,
    BackendRequestTimeoutError,
    BackendResponseValidationError,
)
from cyber_agent_test_core.backend.fake import BackendCall, FakeBackendClient
from cyber_agent_test_core.backend.http import (
    AttachmentSink,
    HTTPAdapter,
    HTTPAttachmentPolicy,
    HTTPRequest,
    HTTPResponse,
)
from cyber_agent_test_core.backend.models import (
    BackendAgentState,
    BackendAgentStatus,
    BackendClientSettings,
    FeatureFlagState,
    PackageMetadata,
    PolicyAssignmentResult,
    ProxyConfiguration,
    RegistrationResult,
    TLSConfiguration,
)

__all__ = [
    "AgentRegistrationAPI",
    "AgentStatusAPI",
    "AttachmentSink",
    "AuthenticationProvider",
    "BackendAgentState",
    "BackendAgentStatus",
    "BackendAuthenticationError",
    "BackendCall",
    "BackendClient",
    "BackendClientSettings",
    "BackendConnectionError",
    "BackendError",
    "BackendHTTPError",
    "BackendRequestTimeoutError",
    "BackendResponseValidationError",
    "FakeBackendClient",
    "FeatureFlagState",
    "FeatureFlagsAPI",
    "HTTPAdapter",
    "HTTPAttachmentPolicy",
    "HTTPBackendClient",
    "HTTPRequest",
    "HTTPResponse",
    "PackageMetadata",
    "PackageMetadataAPI",
    "PolicyAPI",
    "PolicyAssignmentResult",
    "ProxyConfiguration",
    "RefreshingTokenProvider",
    "RegistrationResult",
    "SecretResolver",
    "TLSConfiguration",
]

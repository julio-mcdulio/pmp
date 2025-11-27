 """Custom exceptions for PMP CLI."""


 class PMPError(Exception):
     """Base error raised by PMP."""

     exit_code = 1


 class PromptAlreadyExists(PMPError):
     """Raised when attempting to add a duplicate prompt."""


 class PromptNotFound(PMPError):
     """Raised when a prompt cannot be located."""


 class VersionNotFound(PMPError):
     """Raised when a specific prompt version does not exist."""


 class ConfigError(PMPError):
     """Raised when configuration is invalid or incomplete."""


 class BackendError(PMPError):
     """Raised when the backend reports an unrecoverable issue."""


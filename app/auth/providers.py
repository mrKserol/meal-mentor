from dataclasses import dataclass


@dataclass
class ExternalIdentity:
    provider: str
    provider_user_id: str
    email: str | None = None
    username: str | None = None


class ExternalAuthProvider:
    """Contract for future OAuth/Telegram identity providers."""

    provider_name: str

    def exchange_code(self, code: str) -> ExternalIdentity:  # pragma: no cover - future extension
        raise NotImplementedError

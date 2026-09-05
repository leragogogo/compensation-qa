from __future__ import annotations

from ekisqa.profiles.base import StateProfile


class UnknownProfileError(LookupError):
    """Raised when no such land is registered."""


class ProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, StateProfile] = {}

    def register(self, profile: StateProfile) -> None:
        self._profiles[profile.land_code] = profile

    def resolve(self, land_code: str) -> StateProfile:
        try:
            return self._profiles[land_code]
        except KeyError:
            raise UnknownProfileError(f"No StateProfile registered for land_code={land_code!r}.")

    def land_codes(self) -> list[str]:
        return sorted(self._profiles)


_default_registry: ProfileRegistry | None = None


def default_registry() -> ProfileRegistry:
    """The singleton register across the process, populated with built-in profiles."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ProfileRegistry()
        _register_builtin_profiles(_default_registry)
    return _default_registry


def _register_builtin_profiles(registry: ProfileRegistry) -> None:
    from ekisqa.profiles.brandenburg.profile import build_brandenburg_profile

    registry.register(build_brandenburg_profile())

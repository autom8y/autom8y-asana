"""Tests for service-layer exception hierarchy.

Verifies:
- Exception inheritance chain
- error_code property for each error type
- to_dict() output matches expected API response format
- status_hint property matches expected HTTP status codes
- get_status_for_error() mapping
"""

from __future__ import annotations

import pytest

from autom8_asana.services.errors import (
    CacheNotReadyError,
    EntityNotFoundError,
    EntityTypeMismatchError,
    EntityValidationError,
    InvalidFieldError,
    InvalidParameterError,
    NoValidFieldsError,
    ServiceError,
    ServiceNotConfiguredError,
    TaskNotFoundError,
    UnknownEntityError,
    UnknownSectionError,
    get_status_for_error,
)


class TestServiceErrorBase:
    """Tests for the ServiceError base class."""

    def test_inherits_from_exception(self) -> None:
        assert issubclass(ServiceError, Exception)

    def test_message_attribute(self) -> None:
        err = ServiceError("something went wrong")
        assert err.message == "something went wrong"
        assert str(err) == "something went wrong"

    def test_error_code(self) -> None:
        err = ServiceError("test")
        assert err.error_code == "SERVICE_ERROR"

    def test_status_hint(self) -> None:
        err = ServiceError("test")
        assert err.status_hint == 500

    def test_to_dict(self) -> None:
        err = ServiceError("test message")
        result = err.to_dict()
        assert result == {"error": "SERVICE_ERROR", "message": "test message"}


class TestUnknownEntityError:
    """Tests for UnknownEntityError."""

    def test_inherits_from_entity_not_found(self) -> None:
        assert issubclass(UnknownEntityError, EntityNotFoundError)
        assert issubclass(UnknownEntityError, ServiceError)

    def test_attributes(self) -> None:
        err = UnknownEntityError("widget", ["business", "offer", "unit"])
        assert err.entity_type == "widget"
        assert err.available == ["business", "offer", "unit"]
        assert "widget" in str(err)

    def test_error_code(self) -> None:
        err = UnknownEntityError("widget", [])
        assert err.error_code == "UNKNOWN_ENTITY_TYPE"

    def test_to_dict(self) -> None:
        err = UnknownEntityError("widget", ["offer", "unit"])
        result = err.to_dict()
        assert result["error"] == "UNKNOWN_ENTITY_TYPE"
        assert "widget" in result["message"]
        assert result["available_types"] == ["offer", "unit"]

    def test_status_hint(self) -> None:
        err = UnknownEntityError("x", [])
        assert err.status_hint == 404

    def test_catchable_as_service_error(self) -> None:
        with pytest.raises(ServiceError):
            raise UnknownEntityError("x", [])


class TestUnknownSectionError:
    """Tests for UnknownSectionError."""

    def test_inherits_from_entity_not_found(self) -> None:
        assert issubclass(UnknownSectionError, EntityNotFoundError)

    def test_attributes(self) -> None:
        err = UnknownSectionError("Backlog", ["To Do", "In Progress", "Done"])
        assert err.section_name == "Backlog"
        assert err.available_sections == ["To Do", "In Progress", "Done"]

    def test_to_dict_with_available(self) -> None:
        err = UnknownSectionError("Backlog", ["Done", "To Do"])
        result = err.to_dict()
        assert result["error"] == "UNKNOWN_SECTION"
        assert "Backlog" in result["message"]
        assert result["available_sections"] == ["Done", "To Do"]

    def test_to_dict_without_available(self) -> None:
        err = UnknownSectionError("Backlog")
        result = err.to_dict()
        assert "available_sections" not in result


class TestTaskNotFoundError:
    """Tests for TaskNotFoundError."""

    def test_inherits_from_entity_not_found(self) -> None:
        assert issubclass(TaskNotFoundError, EntityNotFoundError)
        assert issubclass(TaskNotFoundError, ServiceError)

    def test_attributes(self) -> None:
        err = TaskNotFoundError("1234567890")
        assert err.gid == "1234567890"
        assert "1234567890" in str(err)

    def test_error_code(self) -> None:
        err = TaskNotFoundError("123")
        assert err.error_code == "TASK_NOT_FOUND"

    def test_status_hint(self) -> None:
        err = TaskNotFoundError("123")
        assert err.status_hint == 404

    def test_to_dict(self) -> None:
        err = TaskNotFoundError("1234567890")
        result = err.to_dict()
        assert result["error"] == "TASK_NOT_FOUND"
        assert "1234567890" in result["message"]

    def test_catchable_as_entity_not_found(self) -> None:
        with pytest.raises(EntityNotFoundError):
            raise TaskNotFoundError("123")

    def test_catchable_as_service_error(self) -> None:
        with pytest.raises(ServiceError):
            raise TaskNotFoundError("123")


class TestEntityTypeMismatchError:
    """Tests for EntityTypeMismatchError."""

    def test_inherits_from_entity_not_found(self) -> None:
        assert issubclass(EntityTypeMismatchError, EntityNotFoundError)
        assert issubclass(EntityTypeMismatchError, ServiceError)

    def test_attributes(self) -> None:
        err = EntityTypeMismatchError(
            "1234567890", "proj_expected", ["proj_a", "proj_b"]
        )
        assert err.gid == "1234567890"
        assert err.expected_project == "proj_expected"
        assert err.actual_projects == ["proj_a", "proj_b"]

    def test_error_code(self) -> None:
        err = EntityTypeMismatchError("123", "proj_a", ["proj_b"])
        assert err.error_code == "ENTITY_TYPE_MISMATCH"

    def test_status_hint(self) -> None:
        err = EntityTypeMismatchError("123", "proj_a", ["proj_b"])
        assert err.status_hint == 404

    def test_message_contains_context(self) -> None:
        err = EntityTypeMismatchError("123", "proj_expected", ["proj_actual"])
        msg = str(err)
        assert "123" in msg
        assert "proj_expected" in msg
        assert "proj_actual" in msg

    def test_to_dict(self) -> None:
        err = EntityTypeMismatchError(
            "1234567890", "proj_expected", ["proj_a", "proj_b"]
        )
        result = err.to_dict()
        assert result["error"] == "ENTITY_TYPE_MISMATCH"
        assert "1234567890" in result["message"]
        assert result["expected_project"] == "proj_expected"
        assert result["actual_projects"] == ["proj_a", "proj_b"]

    def test_catchable_as_entity_not_found(self) -> None:
        with pytest.raises(EntityNotFoundError):
            raise EntityTypeMismatchError("123", "a", ["b"])

    def test_catchable_as_service_error(self) -> None:
        with pytest.raises(ServiceError):
            raise EntityTypeMismatchError("123", "a", ["b"])


class TestInvalidFieldError:
    """Tests for InvalidFieldError."""

    def test_inherits_chain(self) -> None:
        assert issubclass(InvalidFieldError, EntityValidationError)
        assert issubclass(InvalidFieldError, ServiceError)

    def test_attributes(self) -> None:
        err = InvalidFieldError(
            invalid_fields=["foo", "bar"],
            available_fields=["name", "gid", "status"],
        )
        assert err.invalid_fields == ["foo", "bar"]
        assert err.available_fields == ["name", "gid", "status"]

    def test_error_code(self) -> None:
        err = InvalidFieldError([], [])
        assert err.error_code == "INVALID_FIELD"

    def test_status_hint(self) -> None:
        err = InvalidFieldError([], [])
        assert err.status_hint == 422

    def test_to_dict(self) -> None:
        err = InvalidFieldError(
            invalid_fields=["foo"],
            available_fields=["name", "gid"],
        )
        result = err.to_dict()
        assert result["error"] == "INVALID_FIELD"
        assert result["invalid_fields"] == ["foo"]
        assert result["available_fields"] == ["name", "gid"]


class TestInvalidParameterError:
    """Tests for InvalidParameterError."""

    def test_inherits_from_validation(self) -> None:
        assert issubclass(InvalidParameterError, EntityValidationError)

    def test_error_code(self) -> None:
        err = InvalidParameterError("missing param")
        assert err.error_code == "INVALID_PARAMETER"

    def test_status_hint(self) -> None:
        err = InvalidParameterError("bad")
        assert err.status_hint == 400


class TestNoValidFieldsError:
    """Tests for NoValidFieldsError."""

    def test_inherits_from_entity_validation(self) -> None:
        assert issubclass(NoValidFieldsError, EntityValidationError)
        assert issubclass(NoValidFieldsError, ServiceError)

    def test_error_code(self) -> None:
        err = NoValidFieldsError("all fields failed resolution")
        assert err.error_code == "NO_VALID_FIELDS"

    def test_status_hint(self) -> None:
        err = NoValidFieldsError("no valid fields")
        assert err.status_hint == 422

    def test_to_dict(self) -> None:
        err = NoValidFieldsError("all fields failed resolution")
        result = err.to_dict()
        assert result["error"] == "NO_VALID_FIELDS"
        assert "all fields failed resolution" in result["message"]

    def test_catchable_as_validation_error(self) -> None:
        with pytest.raises(EntityValidationError):
            raise NoValidFieldsError("no valid fields")

    def test_catchable_as_service_error(self) -> None:
        with pytest.raises(ServiceError):
            raise NoValidFieldsError("no valid fields")


class TestCacheNotReadyError:
    """Tests for CacheNotReadyError."""

    def test_inherits_from_service_error(self) -> None:
        assert issubclass(CacheNotReadyError, ServiceError)

    def test_with_entity_type(self) -> None:
        err = CacheNotReadyError("unit")
        assert err.entity_type == "unit"
        assert "unit" in str(err)

    def test_without_entity_type(self) -> None:
        err = CacheNotReadyError()
        assert err.entity_type is None
        assert "Cache not warmed" in str(err)

    def test_error_code(self) -> None:
        err = CacheNotReadyError()
        assert err.error_code == "CACHE_NOT_WARMED"

    def test_status_hint(self) -> None:
        err = CacheNotReadyError()
        assert err.status_hint == 503


class TestServiceNotConfiguredError:
    """Tests for ServiceNotConfiguredError."""

    def test_error_code(self) -> None:
        err = ServiceNotConfiguredError("bot PAT missing")
        assert err.error_code == "SERVICE_NOT_CONFIGURED"

    def test_status_hint(self) -> None:
        err = ServiceNotConfiguredError("missing")
        assert err.status_hint == 503


class TestGetStatusForError:
    """Tests for get_status_for_error() mapping function."""

    def test_unknown_entity_maps_to_404(self) -> None:
        err = UnknownEntityError("widget", [])
        assert get_status_for_error(err) == 404

    def test_unknown_section_maps_to_404(self) -> None:
        err = UnknownSectionError("Backlog")
        assert get_status_for_error(err) == 404

    def test_task_not_found_maps_to_404(self) -> None:
        err = TaskNotFoundError("123")
        assert get_status_for_error(err) == 404

    def test_entity_type_mismatch_maps_to_404(self) -> None:
        err = EntityTypeMismatchError("123", "proj_a", ["proj_b"])
        assert get_status_for_error(err) == 404

    def test_invalid_field_maps_to_422(self) -> None:
        err = InvalidFieldError(["x"], ["y"])
        assert get_status_for_error(err) == 422

    def test_no_valid_fields_maps_to_422(self) -> None:
        err = NoValidFieldsError("no fields")
        assert get_status_for_error(err) == 422

    def test_invalid_parameter_maps_to_400(self) -> None:
        err = InvalidParameterError("bad")
        assert get_status_for_error(err) == 400

    def test_cache_not_ready_maps_to_503(self) -> None:
        err = CacheNotReadyError()
        assert get_status_for_error(err) == 503

    def test_service_not_configured_maps_to_503(self) -> None:
        err = ServiceNotConfiguredError("missing")
        assert get_status_for_error(err) == 503

    def test_base_service_error_maps_to_500(self) -> None:
        err = ServiceError("generic")
        assert get_status_for_error(err) == 500

    def test_no_http_exception_imported(self) -> None:
        """Services must never import or raise HTTPException."""
        import autom8_asana.services.errors as mod

        source = mod.__file__
        assert source is not None
        with open(source) as f:
            content = f.read()
        assert "HTTPException" not in content

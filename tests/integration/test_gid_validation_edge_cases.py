"""Integration tests for GID validation.

Per TDD-TRIAGE-FIXES Issue #5: GID Input Validation.
"""

import pytest
from autom8_asana.persistence.exceptions import ValidationError
from autom8_asana.persistence.validation import validate_gid


class TestGIDValidation:
    """Test GID validation edge cases."""

    def test_valid_gid_simple(self):
        """Valid GID: simple numeric string."""
        validate_gid("1234567890")  # Should not raise

    def test_valid_gid_single_digit(self):
        """Valid GID: single digit."""
        validate_gid("1")  # Should not raise

    def test_valid_gid_max_length(self):
        """Valid GID: maximum 64 characters."""
        validate_gid("1" * 64)  # Should not raise

    def test_invalid_gid_empty_string(self):
        """Invalid GID: empty string."""
        with pytest.raises(ValidationError) as exc:
            validate_gid("")
        assert "empty" in str(exc.value).lower()

    def test_invalid_gid_non_numeric(self):
        """Invalid GID: contains non-numeric characters."""
        with pytest.raises(ValidationError) as exc:
            validate_gid("abc123")
        assert "numeric" in str(exc.value).lower()

    def test_invalid_gid_with_spaces(self):
        """Invalid GID: contains spaces."""
        with pytest.raises(ValidationError) as exc:
            validate_gid(" 123 ")
        assert "numeric" in str(exc.value).lower()

    def test_invalid_gid_none_type(self):
        """Invalid GID: None value."""
        with pytest.raises(ValidationError) as exc:
            validate_gid(None)  # type: ignore[arg-type]
        assert "string" in str(exc.value).lower()

    def test_invalid_gid_integer_type(self):
        """Invalid GID: integer instead of string."""
        with pytest.raises(ValidationError) as exc:
            validate_gid(123)  # type: ignore[arg-type]
        assert "string" in str(exc.value).lower()

    def test_invalid_gid_too_long(self):
        """Invalid GID: exceeds 64 character limit."""
        with pytest.raises(ValidationError) as exc:
            validate_gid("1" * 65)
        assert "64" in str(exc.value) or "length" in str(exc.value).lower()

    def test_valid_gid_leading_zeros(self):
        """Valid GID: leading zeros are numeric, so valid."""
        validate_gid("0000123")  # Should not raise (all digits)

    def test_error_message_includes_param_name(self):
        """Error message includes the parameter name."""
        with pytest.raises(ValidationError) as exc:
            validate_gid("invalid", "custom_param")
        assert "custom_param" in str(exc.value)

    def test_error_message_includes_actual_value(self):
        """Error message includes the invalid value."""
        with pytest.raises(ValidationError) as exc:
            validate_gid("not-a-gid")
        assert "not-a-gid" in str(exc.value)

    def test_invalid_gid_special_characters(self):
        """Invalid GID: contains special characters."""
        with pytest.raises(ValidationError) as exc:
            validate_gid("12@34#56")
        assert "numeric" in str(exc.value).lower()

    def test_invalid_gid_list_type(self):
        """Invalid GID: list type."""
        with pytest.raises(ValidationError) as exc:
            validate_gid(["123"])  # type: ignore[arg-type]
        assert "string" in str(exc.value).lower()

    def test_invalid_gid_dict_type(self):
        """Invalid GID: dict type."""
        with pytest.raises(ValidationError) as exc:
            validate_gid({"gid": "123"})  # type: ignore[arg-type]
        assert "string" in str(exc.value).lower()


class TestSaveSessionGIDValidation:
    """Test GID validation in SaveSession methods.

    Note: These are unit-level tests using mock/fixture objects.
    """

    def test_add_tag_validates_tag_gid(self, client_fixture, task_fixture):
        """add_tag() validates tag_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.add_tag(task_fixture, "invalid-gid")

    def test_remove_tag_validates_tag_gid(self, client_fixture, task_fixture):
        """remove_tag() validates tag_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.remove_tag(task_fixture, "invalid-gid")

    def test_add_to_project_validates_project_gid(self, client_fixture, task_fixture):
        """add_to_project() validates project_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.add_to_project(task_fixture, "invalid-project")

    def test_remove_from_project_validates_project_gid(
        self, client_fixture, task_fixture
    ):
        """remove_from_project() validates project_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.remove_from_project(task_fixture, "invalid-project")

    def test_move_to_section_validates_section_gid(self, client_fixture, task_fixture):
        """move_to_section() validates section_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.move_to_section(task_fixture, "invalid-section")

    def test_add_dependency_validates_dependency_gid(
        self, client_fixture, task_fixture
    ):
        """add_dependency() validates dependency_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.add_dependency(task_fixture, "invalid-dep")

    def test_remove_dependency_validates_dependency_gid(
        self, client_fixture, task_fixture
    ):
        """remove_dependency() validates dependency_gid parameter."""
        from autom8_asana.persistence.session import SaveSession

        session = SaveSession(client_fixture)

        with pytest.raises(ValidationError):
            session.remove_dependency(task_fixture, "invalid-dep")


class TestClientGIDValidation:
    """Test GID validation in client methods.

    Note: These are unit-level tests that verify validation happens
    before API calls are made.
    """

    def test_get_async_validates_task_gid(self, client_fixture):
        """TasksClient.get_async() validates task_gid."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.get_async("invalid-gid")

        asyncio.run(run_test())

    def test_add_tag_async_validates_both_gids(self, client_fixture):
        """TasksClient.add_tag_async() validates both GIDs."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.add_tag_async("invalid-task", "123")

            with pytest.raises(ValidationError):
                await client_fixture.tasks.add_tag_async("123", "invalid-tag")

        asyncio.run(run_test())

    def test_remove_tag_async_validates_both_gids(self, client_fixture):
        """TasksClient.remove_tag_async() validates both GIDs."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.remove_tag_async("invalid-task", "123")

            with pytest.raises(ValidationError):
                await client_fixture.tasks.remove_tag_async("123", "invalid-tag")

        asyncio.run(run_test())

    def test_move_to_section_async_validates_gids(self, client_fixture):
        """TasksClient.move_to_section_async() validates all GIDs."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.move_to_section_async(
                    "invalid-task", "123", "456"
                )

            with pytest.raises(ValidationError):
                await client_fixture.tasks.move_to_section_async(
                    "123", "invalid-section", "456"
                )

            with pytest.raises(ValidationError):
                await client_fixture.tasks.move_to_section_async(
                    "123", "456", "invalid-project"
                )

        asyncio.run(run_test())

    def test_set_assignee_async_validates_both_gids(self, client_fixture):
        """TasksClient.set_assignee_async() validates both GIDs."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.set_assignee_async(
                    "invalid-task", "123"
                )

            with pytest.raises(ValidationError):
                await client_fixture.tasks.set_assignee_async("123", "invalid-user")

        asyncio.run(run_test())

    def test_add_to_project_async_validates_gids(self, client_fixture):
        """TasksClient.add_to_project_async() validates GIDs."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.add_to_project_async(
                    "invalid-task", "123"
                )

            with pytest.raises(ValidationError):
                await client_fixture.tasks.add_to_project_async("123", "invalid-project")

        asyncio.run(run_test())

    def test_remove_from_project_async_validates_gids(self, client_fixture):
        """TasksClient.remove_from_project_async() validates GIDs."""
        import pytest
        import asyncio

        async def run_test():
            with pytest.raises(ValidationError):
                await client_fixture.tasks.remove_from_project_async(
                    "invalid-task", "123"
                )

            with pytest.raises(ValidationError):
                await client_fixture.tasks.remove_from_project_async(
                    "123", "invalid-project"
                )

        asyncio.run(run_test())

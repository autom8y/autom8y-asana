"""Tests for SchemaRegistry singleton.

Verifies singleton behavior, lazy initialization, schema retrieval,
registration, and thread safety.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from autom8_asana.dataframes.errors import SchemaNotFoundError, SchemaVersionError
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset registry before each test for isolation."""
    SchemaRegistry.reset()
    yield
    SchemaRegistry.reset()


class TestSchemaRegistrySingleton:
    """Tests for singleton behavior."""

    def test_same_instance_returned(self) -> None:
        """Verify multiple calls return the same instance."""
        instance1 = SchemaRegistry.get_instance()
        instance2 = SchemaRegistry.get_instance()
        assert instance1 is instance2

    def test_constructor_returns_singleton(self) -> None:
        """Verify constructor also returns singleton."""
        instance1 = SchemaRegistry()
        instance2 = SchemaRegistry()
        assert instance1 is instance2

    def test_get_instance_same_as_constructor(self) -> None:
        """Verify get_instance and constructor return same instance."""
        instance1 = SchemaRegistry.get_instance()
        instance2 = SchemaRegistry()
        assert instance1 is instance2

    def test_reset_creates_new_instance(self) -> None:
        """Verify reset allows creating new instance."""
        instance1 = SchemaRegistry.get_instance()
        SchemaRegistry.reset()
        instance2 = SchemaRegistry.get_instance()
        assert instance1 is not instance2


class TestSchemaRegistryLazyInitialization:
    """Tests for lazy initialization of built-in schemas."""

    def test_schemas_loaded_on_first_access(self) -> None:
        """Verify schemas are loaded on first access."""
        registry = SchemaRegistry.get_instance()

        # Schemas should be loaded when we access them
        schema = registry.get_schema("Unit")
        assert schema.name == "unit"

    def test_built_in_schemas_available(self) -> None:
        """Verify all built-in schemas are registered."""
        registry = SchemaRegistry.get_instance()

        assert registry.has_schema("*")
        assert registry.has_schema("Unit")
        assert registry.has_schema("Contact")


class TestSchemaRegistryGetSchema:
    """Tests for get_schema method."""

    def test_get_unit_schema(self) -> None:
        """Verify get_schema returns Unit schema."""
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema("Unit")

        assert schema.name == "unit"
        assert schema.task_type == "Unit"
        assert len(schema) == 22

    def test_get_contact_schema(self) -> None:
        """Verify get_schema returns Contact schema."""
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema("Contact")

        assert schema.name == "contact"
        assert schema.task_type == "Contact"
        assert len(schema) == 25

    def test_get_base_schema(self) -> None:
        """Verify get_schema with '*' returns base schema."""
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema("*")

        assert schema.name == "base"
        assert schema.task_type == "*"
        assert len(schema) == 13

    def test_unknown_type_falls_back_to_base(self) -> None:
        """Verify unknown task types fall back to base schema."""
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema("UnknownTaskType")

        assert schema.name == "base"
        assert schema.task_type == "*"

    def test_schema_not_found_when_no_base(self) -> None:
        """Verify SchemaNotFoundError when no base schema exists."""
        registry = SchemaRegistry.get_instance()
        # Access to initialize, then clear
        registry._ensure_initialized()

        # Remove the base schema
        with registry._lock:
            del registry._schemas["*"]

        with pytest.raises(SchemaNotFoundError) as exc_info:
            registry.get_schema("UnknownType")

        assert exc_info.value.task_type == "UnknownType"


class TestSchemaRegistryRegister:
    """Tests for register method."""

    def test_register_new_schema(self) -> None:
        """Verify registering a new schema."""
        registry = SchemaRegistry.get_instance()
        custom_schema = DataFrameSchema(
            name="custom",
            task_type="CustomType",
            columns=[ColumnDef("gid", "Utf8", nullable=False)],
            version="1.0.0",
        )

        registry.register("CustomType", custom_schema)

        assert registry.has_schema("CustomType")
        retrieved = registry.get_schema("CustomType")
        assert retrieved.name == "custom"

    def test_register_same_version_is_idempotent(self) -> None:
        """Verify registering same schema twice is idempotent."""
        registry = SchemaRegistry.get_instance()
        schema1 = DataFrameSchema(
            name="test",
            task_type="TestType",
            columns=[ColumnDef("gid", "Utf8")],
            version="1.0.0",
        )
        schema2 = DataFrameSchema(
            name="test",
            task_type="TestType",
            columns=[ColumnDef("gid", "Utf8")],
            version="1.0.0",
        )

        registry.register("TestType", schema1)
        # Should not raise
        registry.register("TestType", schema2)

    def test_register_different_version_raises_error(self) -> None:
        """Verify SchemaVersionError for version conflicts."""
        registry = SchemaRegistry.get_instance()
        schema1 = DataFrameSchema(
            name="test",
            task_type="TestType",
            columns=[ColumnDef("gid", "Utf8")],
            version="1.0.0",
        )
        schema2 = DataFrameSchema(
            name="test",
            task_type="TestType",
            columns=[ColumnDef("gid", "Utf8")],
            version="2.0.0",
        )

        registry.register("TestType", schema1)

        with pytest.raises(SchemaVersionError) as exc_info:
            registry.register("TestType", schema2)

        assert exc_info.value.expected_version == "1.0.0"
        assert exc_info.value.actual_version == "2.0.0"

    def test_register_with_allow_override(self) -> None:
        """Verify allow_override allows replacing schema."""
        registry = SchemaRegistry.get_instance()
        schema1 = DataFrameSchema(
            name="test",
            task_type="TestType",
            columns=[ColumnDef("gid", "Utf8")],
            version="1.0.0",
        )
        schema2 = DataFrameSchema(
            name="test_v2",
            task_type="TestType",
            columns=[ColumnDef("gid", "Utf8"), ColumnDef("name", "Utf8")],
            version="2.0.0",
        )

        registry.register("TestType", schema1)
        registry.register("TestType", schema2, allow_override=True)

        retrieved = registry.get_schema("TestType")
        assert retrieved.name == "test_v2"
        assert retrieved.version == "2.0.0"


class TestSchemaRegistryHasSchema:
    """Tests for has_schema method."""

    def test_has_schema_returns_true_for_registered(self) -> None:
        """Verify has_schema returns True for registered schemas."""
        registry = SchemaRegistry.get_instance()
        assert registry.has_schema("Unit") is True
        assert registry.has_schema("Contact") is True
        assert registry.has_schema("*") is True

    def test_has_schema_returns_false_for_unregistered(self) -> None:
        """Verify has_schema returns False for unregistered schemas."""
        registry = SchemaRegistry.get_instance()
        assert registry.has_schema("NotRegistered") is False


class TestSchemaRegistryListTaskTypes:
    """Tests for list_task_types method."""

    def test_list_task_types_excludes_wildcard(self) -> None:
        """Verify list_task_types excludes '*' (base schema)."""
        registry = SchemaRegistry.get_instance()
        types = registry.list_task_types()

        assert "*" not in types
        assert "Unit" in types
        assert "Contact" in types

    def test_list_task_types_includes_custom(self) -> None:
        """Verify list_task_types includes custom registrations."""
        registry = SchemaRegistry.get_instance()
        custom_schema = DataFrameSchema(
            name="custom",
            task_type="CustomType",
            columns=[ColumnDef("gid", "Utf8")],
        )
        registry.register("CustomType", custom_schema)

        types = registry.list_task_types()
        assert "CustomType" in types


class TestSchemaRegistryGetAllSchemas:
    """Tests for get_all_schemas method."""

    def test_get_all_schemas_returns_copy(self) -> None:
        """Verify get_all_schemas returns a copy."""
        registry = SchemaRegistry.get_instance()
        schemas = registry.get_all_schemas()

        # Modifying returned dict should not affect registry
        schemas["NewType"] = DataFrameSchema(name="new", task_type="NewType", columns=[])
        assert not registry.has_schema("NewType")

    def test_get_all_schemas_includes_all_registered(self) -> None:
        """Verify get_all_schemas includes all registered schemas."""
        registry = SchemaRegistry.get_instance()
        schemas = registry.get_all_schemas()

        assert "*" in schemas
        assert "Unit" in schemas
        assert "Contact" in schemas


class TestSchemaRegistryThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_get_schema(self) -> None:
        """Verify concurrent get_schema calls are thread-safe."""
        registry = SchemaRegistry.get_instance()
        results: list[DataFrameSchema] = []
        errors: list[Exception] = []

        def get_unit_schema() -> None:
            try:
                schema = registry.get_schema("Unit")
                results.append(schema)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_unit_schema) for _ in range(100)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        assert len(results) == 100
        # All should be the same schema
        assert all(r.name == "unit" for r in results)

    def test_concurrent_register(self) -> None:
        """Verify concurrent register calls are thread-safe."""
        registry = SchemaRegistry.get_instance()
        errors: list[Exception] = []

        def register_schema(i: int) -> None:
            try:
                schema = DataFrameSchema(
                    name=f"schema_{i}",
                    task_type=f"Type_{i}",
                    columns=[ColumnDef("gid", "Utf8")],
                )
                registry.register(f"Type_{i}", schema)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_schema, i) for i in range(50)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        # All schemas should be registered
        for i in range(50):
            assert registry.has_schema(f"Type_{i}")

    def test_singleton_thread_safety(self) -> None:
        """Verify singleton creation is thread-safe."""
        SchemaRegistry.reset()
        instances: list[SchemaRegistry] = []

        def get_instance() -> None:
            instance = SchemaRegistry.get_instance()
            instances.append(instance)

        threads = [threading.Thread(target=get_instance) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        # All instances should be the same object
        assert len(instances) == 20
        assert all(inst is instances[0] for inst in instances)

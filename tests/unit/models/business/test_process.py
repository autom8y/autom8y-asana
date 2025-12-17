"""Tests for Process and ProcessHolder models.

Per TDD-BIZMODEL: Tests for Process base model (forward-compatible for Phase 2).
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.process import Process, ProcessHolder, ProcessType
from autom8_asana.models.business.unit import Unit, UnitHolder
from autom8_asana.models.task import Task


class TestProcess:
    """Tests for Process model."""

    def test_process_inherits_from_task(self) -> None:
        """Process inherits from Task and can be constructed."""
        process = Process(gid="123", name="Onboarding Process")
        assert process.gid == "123"
        assert process.name == "Onboarding Process"


class TestProcessType:
    """Tests for ProcessType enum."""

    def test_process_type_generic(self) -> None:
        """ProcessType.GENERIC is available."""
        assert ProcessType.GENERIC.value == "generic"

    def test_process_type_property_returns_generic(self) -> None:
        """process_type property returns GENERIC in Phase 1."""
        process = Process(gid="123", name="Test Process")
        assert process.process_type == ProcessType.GENERIC


class TestProcessNavigation:
    """Tests for Process navigation properties."""

    def test_process_holder_property(self) -> None:
        """process_holder returns cached reference."""
        process = Process(gid="123")
        holder = ProcessHolder(gid="456")
        process._process_holder = holder
        assert process.process_holder is holder

    def test_unit_navigation_via_holder(self) -> None:
        """unit property navigates via process_holder."""
        unit = Unit(gid="u1", name="Test Unit")
        holder = ProcessHolder(gid="h1")
        holder._unit = unit

        process = Process(gid="p1")
        process._process_holder = holder

        assert process.unit is unit

    def test_business_navigation_via_unit(self) -> None:
        """business property navigates via unit."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="b1", name="Test Business")
        unit_holder = UnitHolder(gid="uh1")
        unit_holder._business = business
        unit = Unit(gid="u1")
        unit._unit_holder = unit_holder

        process_holder = ProcessHolder(gid="ph1")
        process_holder._unit = unit

        process = Process(gid="p1")
        process._process_holder = process_holder

        assert process.business is business

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        process = Process(gid="123")
        process._business = object()  # type: ignore
        process._unit = Unit(gid="456")
        process._process_holder = ProcessHolder(gid="789")

        process._invalidate_refs()

        assert process._business is None
        assert process._unit is None
        assert process._process_holder is None


class TestProcessCustomFields:
    """Tests for Process base custom field accessors."""

    def test_status_enum(self) -> None:
        """status extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Status", "enum_value": {"name": "In Progress"}}
            ],
        )
        assert process.status == "In Progress"

    def test_status_setter(self) -> None:
        """status setter updates value."""
        process = Process(gid="123", custom_fields=[])
        process.status = "Completed"
        assert process.get_custom_fields().get("Status") == "Completed"

    def test_priority_enum(self) -> None:
        """priority extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Priority", "enum_value": {"name": "High"}}
            ],
        )
        assert process.priority == "High"

    def test_priority_setter(self) -> None:
        """priority setter updates value."""
        process = Process(gid="123", custom_fields=[])
        process.priority = "Low"
        assert process.get_custom_fields().get("Priority") == "Low"

    def test_assigned_to_people_field(self) -> None:
        """assigned_to returns list of people dicts."""
        process = Process(gid="123", custom_fields=[])
        # Use set() method to properly add multi-value fields
        process.get_custom_fields().set("Assigned To", [
            {"gid": "u1", "name": "John Doe"},
            {"gid": "u2", "name": "Jane Smith"},
        ])
        assert len(process.assigned_to) == 2
        assert process.assigned_to[0]["name"] == "John Doe"

    def test_assigned_to_empty(self) -> None:
        """assigned_to returns empty list when not set."""
        process = Process(gid="123", custom_fields=[])
        assert process.assigned_to == []

    def test_process_due_date(self) -> None:
        """process_due_date getter/setter works."""
        process = Process(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Due Date", "text_value": "2024-12-31"}],
        )
        assert process.process_due_date == "2024-12-31"

    def test_started_at(self) -> None:
        """started_at getter/setter works."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Started At", "text_value": "2024-01-15T10:00:00Z"}
            ],
        )
        assert process.started_at == "2024-01-15T10:00:00Z"

    def test_process_completed_at(self) -> None:
        """process_completed_at getter/setter works."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Process Completed At",
                    "text_value": "2024-01-20T15:30:00Z",
                }
            ],
        )
        assert process.process_completed_at == "2024-01-20T15:30:00Z"

    def test_process_notes(self) -> None:
        """process_notes getter/setter works."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Process Notes", "text_value": "Process notes"}
            ],
        )
        assert process.process_notes == "Process notes"

    def test_vertical_enum(self) -> None:
        """vertical extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        assert process.vertical == "Healthcare"


class TestProcessHolder:
    """Tests for ProcessHolder model."""

    def test_processes_property_empty(self) -> None:
        """processes returns empty list by default."""
        holder = ProcessHolder(gid="123")
        assert holder.processes == []

    def test_processes_property_populated(self) -> None:
        """processes returns populated list."""
        holder = ProcessHolder(gid="123")
        holder._processes = [
            Process(gid="p1", name="Process 1"),
            Process(gid="p2", name="Process 2"),
        ]
        assert len(holder.processes) == 2
        assert holder.processes[0].name == "Process 1"

    def test_unit_property(self) -> None:
        """unit returns cached reference."""
        holder = ProcessHolder(gid="123")
        unit = Unit(gid="u1")
        holder._unit = unit
        assert holder.unit is unit

    def test_business_navigation_via_unit(self) -> None:
        """business navigates via unit."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="b1")
        unit_holder = UnitHolder(gid="uh1")
        unit_holder._business = business
        unit = Unit(gid="u1")
        unit._unit_holder = unit_holder

        holder = ProcessHolder(gid="ph1")
        holder._unit = unit

        assert holder.business is business

    def test_populate_children(self) -> None:
        """_populate_children converts Tasks to Processes."""
        holder = ProcessHolder(gid="123")
        subtasks = [
            Task(gid="p1", name="Process 1", created_at="2024-01-01T00:00:00Z"),
            Task(gid="p2", name="Process 2", created_at="2024-01-02T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        assert len(holder.processes) == 2
        assert all(isinstance(p, Process) for p in holder.processes)
        # Sorted by created_at
        assert holder.processes[0].name == "Process 1"
        assert holder.processes[1].name == "Process 2"

    def test_populate_children_sets_back_references(self) -> None:
        """_populate_children sets back references on processes."""
        unit = Unit(gid="u1")
        holder = ProcessHolder(gid="123")
        holder._unit = unit

        subtasks = [Task(gid="p1", name="Process 1")]
        holder._populate_children(subtasks)

        assert holder.processes[0]._process_holder is holder
        assert holder.processes[0]._unit is unit

    def test_invalidate_cache(self) -> None:
        """invalidate_cache clears processes list."""
        holder = ProcessHolder(gid="123")
        holder._processes = [Process(gid="p1")]
        holder.invalidate_cache()
        assert holder._processes == []


class TestProcessTypeEnum:
    """Tests for ProcessType enum extensibility."""

    def test_process_type_is_string_enum(self) -> None:
        """ProcessType is a string enum."""
        assert isinstance(ProcessType.GENERIC, str)
        assert ProcessType.GENERIC == "generic"

    def test_process_type_enum_member_count(self) -> None:
        """Phase 1 has only GENERIC type."""
        members = list(ProcessType)
        assert len(members) == 1
        assert ProcessType.GENERIC in members

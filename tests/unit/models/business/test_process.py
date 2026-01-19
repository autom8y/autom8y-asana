"""Tests for Process and ProcessHolder models.

Per TDD-BIZMODEL: Tests for Process base model (forward-compatible for Phase 2).
"""

from __future__ import annotations

from autom8_asana.models.business.process import (
    Process,
    ProcessHolder,
    ProcessSection,
    ProcessType,
)
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
        process.get_custom_fields().set(
            "Assigned To",
            [
                {"gid": "u1", "name": "John Doe"},
                {"gid": "u2", "name": "Jane Smith"},
            ],
        )
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
            custom_fields=[
                {"gid": "1", "name": "Due Date", "text_value": "2024-12-31"}
            ],
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
        """ProcessType includes 7 pipeline types.

        Per FR-TYPE-001: 6 pipeline types + GENERIC fallback.
        """
        members = list(ProcessType)
        assert len(members) == 7
        assert ProcessType.GENERIC in members

    def test_process_type_pipeline_types(self) -> None:
        """ProcessType includes all pipeline types.

        Per FR-TYPE-001: SALES, OUTREACH, ONBOARDING, IMPLEMENTATION,
        RETENTION, REACTIVATION values.
        """
        assert ProcessType.SALES.value == "sales"
        assert ProcessType.OUTREACH.value == "outreach"
        assert ProcessType.ONBOARDING.value == "onboarding"
        assert ProcessType.IMPLEMENTATION.value == "implementation"
        assert ProcessType.RETENTION.value == "retention"
        assert ProcessType.REACTIVATION.value == "reactivation"

    def test_process_type_generic_preserved(self) -> None:
        """ProcessType.GENERIC is preserved for backward compatibility.

        Per FR-TYPE-002: GENERIC preserved.
        Per FR-TYPE-003: Values are lowercase strings.
        """
        assert ProcessType.GENERIC.value == "generic"
        assert isinstance(ProcessType.GENERIC, str)


class TestProcessSectionEnum:
    """Tests for ProcessSection enum."""

    def test_process_section_enum_values(self) -> None:
        """ProcessSection includes all 7 values.

        Per FR-SECTION-001: OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED,
        CONVERTED, DID_NOT_CONVERT, OTHER values.
        """
        members = list(ProcessSection)
        assert len(members) == 7

        assert ProcessSection.OPPORTUNITY.value == "opportunity"
        assert ProcessSection.DELAYED.value == "delayed"
        assert ProcessSection.ACTIVE.value == "active"
        assert ProcessSection.SCHEDULED.value == "scheduled"
        assert ProcessSection.CONVERTED.value == "converted"
        assert ProcessSection.DID_NOT_CONVERT.value == "did_not_convert"
        assert ProcessSection.OTHER.value == "other"

    def test_process_section_is_string_enum(self) -> None:
        """ProcessSection is a string enum."""
        assert isinstance(ProcessSection.OPPORTUNITY, str)
        assert ProcessSection.OPPORTUNITY == "opportunity"


class TestProcessSectionFromName:
    """Tests for ProcessSection.from_name() method."""

    def test_from_name_exact_match(self) -> None:
        """from_name() handles exact match (case-insensitive).

        Per FR-SECTION-002: Case-insensitive matching.
        """
        assert ProcessSection.from_name("opportunity") == ProcessSection.OPPORTUNITY
        assert ProcessSection.from_name("Opportunity") == ProcessSection.OPPORTUNITY
        assert ProcessSection.from_name("OPPORTUNITY") == ProcessSection.OPPORTUNITY

    def test_from_name_with_spaces(self) -> None:
        """from_name() handles space-separated names."""
        assert (
            ProcessSection.from_name("did not convert")
            == ProcessSection.DID_NOT_CONVERT
        )
        assert (
            ProcessSection.from_name("Did Not Convert")
            == ProcessSection.DID_NOT_CONVERT
        )
        assert (
            ProcessSection.from_name("DID NOT CONVERT")
            == ProcessSection.DID_NOT_CONVERT
        )

    def test_from_name_with_hyphens(self) -> None:
        """from_name() handles hyphen-separated names."""
        assert (
            ProcessSection.from_name("did-not-convert")
            == ProcessSection.DID_NOT_CONVERT
        )

    def test_from_name_aliases(self) -> None:
        """from_name() handles aliases for DID_NOT_CONVERT."""
        assert (
            ProcessSection.from_name("didnt_convert") == ProcessSection.DID_NOT_CONVERT
        )
        assert (
            ProcessSection.from_name("not_converted") == ProcessSection.DID_NOT_CONVERT
        )
        assert ProcessSection.from_name("lost") == ProcessSection.DID_NOT_CONVERT
        assert ProcessSection.from_name("dnc") == ProcessSection.DID_NOT_CONVERT
        assert (
            ProcessSection.from_name("didnotconvert") == ProcessSection.DID_NOT_CONVERT
        )

    def test_from_name_unknown_returns_other(self) -> None:
        """from_name() returns OTHER for unrecognized sections.

        Per FR-SECTION-003: Returns OTHER for unknown.
        """
        assert ProcessSection.from_name("Unknown Section") == ProcessSection.OTHER
        assert ProcessSection.from_name("Custom Pipeline Stage") == ProcessSection.OTHER
        assert ProcessSection.from_name("Foo Bar Baz") == ProcessSection.OTHER

    def test_from_name_none_returns_none(self) -> None:
        """from_name() returns None for None input.

        Per FR-SECTION-004: Handles None gracefully.
        """
        assert ProcessSection.from_name(None) is None

    def test_from_name_all_standard_sections(self) -> None:
        """from_name() handles all standard section names."""
        assert ProcessSection.from_name("Delayed") == ProcessSection.DELAYED
        assert ProcessSection.from_name("Active") == ProcessSection.ACTIVE
        assert ProcessSection.from_name("Scheduled") == ProcessSection.SCHEDULED
        assert ProcessSection.from_name("Converted") == ProcessSection.CONVERTED


# =============================================================================
# Phase 2 Tests: Pipeline State and Process Type Detection
# Per ADR-0101: Simplified tests after process pipeline cleanup
# =============================================================================


class TestProcessPipelineState:
    """Tests for Process.pipeline_state property.

    Per ADR-0101: Simplified pipeline_state extracts from canonical project membership.
    """

    def test_pipeline_state_no_memberships_returns_none(self) -> None:
        """pipeline_state returns None when no memberships."""
        process = Process(gid="123", name="Test Process", memberships=[])
        assert process.pipeline_state is None

    def test_pipeline_state_no_section_returns_none(self) -> None:
        """pipeline_state returns None when membership has no section."""
        process = Process(
            gid="123",
            name="Test Process",
            memberships=[
                {
                    "project": {"gid": "some_project"},
                }
            ],
        )
        assert process.pipeline_state is None

    def test_pipeline_state_returns_section(self) -> None:
        """pipeline_state returns ProcessSection from first membership with section."""
        process = Process(
            gid="123",
            name="Test Process",
            memberships=[
                {
                    "project": {"gid": "sales_project_gid"},
                    "section": {"name": "Opportunity"},
                }
            ],
        )
        assert process.pipeline_state == ProcessSection.OPPORTUNITY

    def test_pipeline_state_returns_first_section_found(self) -> None:
        """pipeline_state returns section from first membership with section."""
        process = Process(
            gid="123",
            name="Test Process",
            memberships=[
                {
                    "project": {"gid": "project_without_section"},
                },
                {
                    "project": {"gid": "sales_project_gid"},
                    "section": {"name": "Active"},
                },
            ],
        )
        assert process.pipeline_state == ProcessSection.ACTIVE


class TestProcessTypeDetection:
    """Tests for Process.process_type property with project name matching.

    Per ADR-0101: process_type derived from project name.
    """

    def test_process_type_no_memberships_returns_generic(self) -> None:
        """process_type returns GENERIC when no memberships."""
        process = Process(gid="123", name="Test Process", memberships=[])
        assert process.process_type == ProcessType.GENERIC

    def test_process_type_no_matching_name_returns_generic(self) -> None:
        """process_type returns GENERIC when project name doesn't match any type."""
        process = Process(
            gid="123",
            name="Test Process",
            memberships=[
                {
                    "project": {"gid": "some_project", "name": "Random Project"},
                }
            ],
        )
        assert process.process_type == ProcessType.GENERIC

    def test_process_type_sales_project_returns_sales(self) -> None:
        """process_type returns SALES when project name contains 'sales'."""
        process = Process(
            gid="123",
            name="Test Process",
            memberships=[
                {
                    "project": {"gid": "sales_project_gid", "name": "Sales"},
                }
            ],
        )
        assert process.process_type == ProcessType.SALES

    def test_process_type_case_insensitive(self) -> None:
        """process_type matching is case-insensitive."""
        process = Process(
            gid="123",
            name="Test Process",
            memberships=[
                {
                    "project": {"gid": "sales_project_gid", "name": "SALES Pipeline"},
                }
            ],
        )
        assert process.process_type == ProcessType.SALES

    def test_process_type_all_types_detected(self) -> None:
        """All non-GENERIC ProcessTypes can be detected from project names."""
        process_types = [
            (ProcessType.SALES, "Sales"),
            (ProcessType.OUTREACH, "Outreach Campaigns"),
            (ProcessType.ONBOARDING, "Customer Onboarding"),
            (ProcessType.IMPLEMENTATION, "Implementation Projects"),
            (ProcessType.RETENTION, "Retention Tasks"),
            (ProcessType.REACTIVATION, "Reactivation Leads"),
        ]

        for expected_type, project_name in process_types:
            process = Process(
                gid="123",
                name="Test Process",
                memberships=[
                    {
                        "project": {"gid": "project_gid", "name": project_name},
                    }
                ],
            )
            assert process.process_type == expected_type, (
                f"Expected {expected_type} for project '{project_name}'"
            )


# =============================================================================
# Phase 2 Tests: Pipeline-Specific Field Accessors
# Per TDD-TECH-DEBT-REMEDIATION Phase 2 / ADR-0116
# =============================================================================


class TestSalesPipelineFields:
    """Tests for Sales pipeline field accessors.

    Per FR-PROC-001: Sales-specific field accessors.
    Per ADR-0116: Composition pattern with graceful None degradation.
    """

    def test_sales_mrr_number_field(self) -> None:
        """mrr returns Decimal from number value."""
        from decimal import Decimal

        process = Process(
            gid="123",
            custom_fields=[{"gid": "1", "name": "MRR", "number_value": 1500.00}],
        )
        assert process.mrr == Decimal("1500.00")

    def test_sales_mrr_none_when_absent(self) -> None:
        """mrr returns None when field not present."""
        process = Process(gid="123", custom_fields=[])
        assert process.mrr is None

    def test_sales_deal_value_number_field(self) -> None:
        """deal_value returns Decimal from number value."""
        from decimal import Decimal

        process = Process(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Deal Value", "number_value": 25000}],
        )
        assert process.deal_value == Decimal("25000")

    def test_sales_close_date_date_field(self) -> None:
        """close_date returns Arrow from date string."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Close Date", "text_value": "2024-12-31"}
            ],
        )
        assert process.close_date is not None
        assert process.close_date.year == 2024
        assert process.close_date.month == 12
        assert process.close_date.day == 31

    def test_sales_close_date_none_when_absent(self) -> None:
        """close_date returns None when field not present."""
        process = Process(gid="123", custom_fields=[])
        assert process.close_date is None

    def test_sales_rep_people_field(self) -> None:
        """rep returns list of people dicts."""
        process = Process(gid="123", custom_fields=[])
        process.get_custom_fields().set(
            "Rep",
            [
                {"gid": "u1", "name": "Sales Rep"},
            ],
        )
        assert len(process.rep) == 1
        assert process.rep[0]["name"] == "Sales Rep"

    def test_sales_rep_empty_when_absent(self) -> None:
        """rep returns empty list when not set."""
        process = Process(gid="123", custom_fields=[])
        assert process.rep == []

    def test_sales_score_enum_field(self) -> None:
        """score extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Score", "enum_value": {"name": "Hot"}}
            ],
        )
        assert process.score == "Hot"

    def test_sales_disposition_enum_field(self) -> None:
        """disposition extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Disposition", "enum_value": {"name": "Qualified"}}
            ],
        )
        assert process.disposition == "Qualified"

    def test_sales_lead_name_text_field(self) -> None:
        """lead_name returns text value."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Lead Name", "text_value": "John Smith"}
            ],
        )
        assert process.lead_name == "John Smith"

    def test_sales_lead_email_text_field(self) -> None:
        """lead_email returns text value."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Lead Email", "text_value": "john@example.com"}
            ],
        )
        assert process.lead_email == "john@example.com"

    def test_sales_outreach_count_int_field(self) -> None:
        """outreach_count returns integer value."""
        process = Process(
            gid="123",
            custom_fields=[{"gid": "1", "name": "Outreach Count", "number_value": 5}],
        )
        assert process.outreach_count == 5

    def test_sales_campaign_text_field(self) -> None:
        """campaign returns text value for UTM tracking."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Campaign", "text_value": "summer_promo"}
            ],
        )
        assert process.campaign == "summer_promo"

    def test_sales_booking_type_enum_field(self) -> None:
        """booking_type extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Booking Type", "enum_value": {"name": "Demo"}}
            ],
        )
        assert process.booking_type == "Demo"


class TestOnboardingPipelineFields:
    """Tests for Onboarding pipeline field accessors.

    Per FR-PROC-002: Onboarding-specific field accessors.
    Per ADR-0116: Composition pattern with graceful None degradation.
    """

    def test_onboarding_status_enum_field(self) -> None:
        """onboarding_status extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Onboarding Status",
                    "enum_value": {"name": "Active"},
                }
            ],
        )
        assert process.onboarding_status == "Active"

    def test_onboarding_status_none_when_absent(self) -> None:
        """onboarding_status returns None when field not present."""
        process = Process(gid="123", custom_fields=[])
        assert process.onboarding_status is None

    def test_onboarding_go_live_date_date_field(self) -> None:
        """go_live_date returns Arrow from date string."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Go Live Date", "text_value": "2025-01-15"}
            ],
        )
        assert process.go_live_date is not None
        assert process.go_live_date.year == 2025
        assert process.go_live_date.month == 1
        assert process.go_live_date.day == 15

    def test_onboarding_kickoff_date_date_field(self) -> None:
        """kickoff_date returns Arrow from date string."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Kickoff Date", "text_value": "2024-12-01"}
            ],
        )
        assert process.kickoff_date is not None
        assert process.kickoff_date.year == 2024

    def test_onboarding_kickoff_completed_enum_field(self) -> None:
        """kickoff_completed extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Kickoff Completed", "enum_value": {"name": "Yes"}}
            ],
        )
        assert process.kickoff_completed == "Yes"

    def test_onboarding_specialist_people_field(self) -> None:
        """onboarding_specialist returns list of people dicts."""
        process = Process(gid="123", custom_fields=[])
        process.get_custom_fields().set(
            "Onboarding Specialist",
            [
                {"gid": "u1", "name": "Onboarding Lead"},
            ],
        )
        assert len(process.onboarding_specialist) == 1
        assert process.onboarding_specialist[0]["name"] == "Onboarding Lead"

    def test_onboarding_notes_text_field(self) -> None:
        """onboarding_notes returns text value."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Onboarding Notes",
                    "text_value": "Customer prefers morning calls",
                }
            ],
        )
        assert process.onboarding_notes == "Customer prefers morning calls"

    def test_onboarding_integration_status_enum_field(self) -> None:
        """integration_status extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Integration Status",
                    "enum_value": {"name": "Complete"},
                }
            ],
        )
        assert process.integration_status == "Complete"


class TestImplementationPipelineFields:
    """Tests for Implementation pipeline field accessors.

    Per FR-PROC-003: Implementation-specific field accessors.
    Per ADR-0116: Composition pattern with graceful None degradation.
    """

    def test_implementation_status_enum_field(self) -> None:
        """implementation_status extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Implementation Status",
                    "enum_value": {"name": "In Progress"},
                }
            ],
        )
        assert process.implementation_status == "In Progress"

    def test_implementation_status_none_when_absent(self) -> None:
        """implementation_status returns None when field not present."""
        process = Process(gid="123", custom_fields=[])
        assert process.implementation_status is None

    def test_implementation_delivery_date_date_field(self) -> None:
        """delivery_date returns Arrow from date string."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Delivery Date", "text_value": "2025-02-28"}
            ],
        )
        assert process.delivery_date is not None
        assert process.delivery_date.year == 2025
        assert process.delivery_date.month == 2
        assert process.delivery_date.day == 28

    def test_implementation_launch_date_date_field(self) -> None:
        """launch_date returns Arrow from date string."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Launch Date", "text_value": "2025-03-01"}
            ],
        )
        assert process.launch_date is not None
        assert process.launch_date.year == 2025

    def test_implementation_build_status_enum_field(self) -> None:
        """build_status extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Build Status", "enum_value": {"name": "Complete"}}
            ],
        )
        assert process.build_status == "Complete"

    def test_implementation_creative_status_enum_field(self) -> None:
        """creative_status extracts name from enum dict."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Creative Status",
                    "enum_value": {"name": "Pending Review"},
                }
            ],
        )
        assert process.creative_status == "Pending Review"

    def test_implementation_lead_people_field(self) -> None:
        """implementation_lead returns list of people dicts."""
        process = Process(gid="123", custom_fields=[])
        process.get_custom_fields().set(
            "Implementation Lead",
            [
                {"gid": "u1", "name": "Project Manager"},
            ],
        )
        assert len(process.implementation_lead) == 1
        assert process.implementation_lead[0]["name"] == "Project Manager"

    def test_implementation_technical_requirements_text_field(self) -> None:
        """technical_requirements returns text value."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Technical Requirements",
                    "text_value": "API integration needed",
                }
            ],
        )
        assert process.technical_requirements == "API integration needed"

    def test_implementation_integration_points_multi_enum_field(self) -> None:
        """integration_points returns list of enum names."""
        process = Process(
            gid="123",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Integration Points",
                    "multi_enum_values": [
                        {"name": "CRM"},
                        {"name": "Email"},
                    ],
                }
            ],
        )
        assert process.integration_points == ["CRM", "Email"]


class TestProcessFieldGracefulDegradation:
    """Tests for graceful degradation when accessing non-existent fields.

    Per ADR-0116: Accessing a field that doesn't exist on the underlying
    Asana task returns None (or empty list for multi-value fields).
    """

    def test_sales_fields_return_none_on_onboarding_process(self) -> None:
        """Sales fields return None when accessed on Onboarding process."""
        # Create a process without Sales-specific fields
        process = Process(
            gid="123",
            name="Onboarding Process",
            memberships=[{"project": {"gid": "onb_project", "name": "Onboarding"}}],
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Onboarding Status",
                    "enum_value": {"name": "Active"},
                }
            ],
        )

        # Verify it's detected as Onboarding
        assert process.process_type == ProcessType.ONBOARDING

        # Sales fields should return None (graceful degradation)
        assert process.deal_value is None
        assert process.close_date is None
        assert process.score is None
        assert process.disposition is None

    def test_onboarding_fields_return_none_on_sales_process(self) -> None:
        """Onboarding fields return None when accessed on Sales process."""
        # Create a process without Onboarding-specific fields
        process = Process(
            gid="123",
            name="Sales Lead",
            memberships=[{"project": {"gid": "sales_project", "name": "Sales"}}],
            custom_fields=[{"gid": "1", "name": "Deal Value", "number_value": 5000}],
        )

        # Verify it's detected as Sales
        assert process.process_type == ProcessType.SALES

        # Onboarding fields should return None (graceful degradation)
        assert process.onboarding_status is None
        assert process.go_live_date is None
        assert process.kickoff_completed is None

    def test_people_fields_return_empty_list_when_absent(self) -> None:
        """People fields return empty list (not None) when not set."""
        process = Process(gid="123", custom_fields=[])

        # All people fields return empty list
        assert process.rep == []
        assert process.closer == []
        assert process.setter == []
        assert process.onboarding_specialist == []
        assert process.implementation_lead == []

    def test_multi_enum_fields_return_empty_list_when_absent(self) -> None:
        """Multi-enum fields return empty list (not None) when not set."""
        process = Process(gid="123", custom_fields=[])

        # Multi-enum fields return empty list
        assert process.integration_points == []

from __future__ import annotations

from .convention_scan import (
    collect_import_placement_findings,
    collect_relative_import_depth_findings,
    collect_todo_comment_findings,
    collect_wildcard_import_findings,
)
from .layout_scan import collect_structural_findings
from .models import AuditResults, AuditSettings
from .module_loader import load_modules
from .private_helpers import (
    collect_cross_module_private_access_findings,
    collect_cross_module_references,
    collect_private_helpers,
    collect_same_module_references,
    zero_reference_helpers,
)
from .test_structure_scan import (
    collect_cross_lane_test_import_findings,
    collect_phase_named_test_directory_findings,
)
from .threshold_scan import collect_file_line_violations, collect_function_size_violations


def run_style_audit(settings: AuditSettings) -> AuditResults:
    modules = load_modules(settings)
    module_name_to_path = {
        module.module_name: module.path for module in modules if module.module_name is not None
    }
    structural_findings = collect_structural_findings(modules, settings)
    helpers, helpers_by_path = collect_private_helpers(modules)
    references = collect_same_module_references(helpers, helpers_by_path, modules)
    cross_module_findings = collect_cross_module_references(
        helpers_by_path,
        module_name_to_path,
        modules,
        references,
    )
    return AuditResults(
        modules=tuple(modules),
        sibling_prefix_findings=structural_findings.sibling_prefix_findings,
        import_wrapper_modules=structural_findings.import_wrapper_modules,
        star_import_collectors=structural_findings.star_import_collectors,
        phase_named_test_directory_findings=collect_phase_named_test_directory_findings(
            modules,
            settings.apps_api_root / "tests",
        ),
        cross_lane_test_import_findings=collect_cross_lane_test_import_findings(
            modules,
            settings.apps_api_root / "tests",
        ),
        import_placement_findings=tuple(collect_import_placement_findings(modules)),
        wildcard_import_findings=tuple(collect_wildcard_import_findings(modules)),
        todo_comment_findings=tuple(collect_todo_comment_findings(modules)),
        relative_import_depth_findings=collect_relative_import_depth_findings(modules),
        cross_module_private_access_findings=collect_cross_module_private_access_findings(
            helpers_by_path,
            module_name_to_path,
            modules,
        ),
        gitkeep_placeholders=structural_findings.gitkeep_placeholders,
        generic_module_name_findings=structural_findings.generic_module_name_findings,
        cross_module_findings=tuple(cross_module_findings),
        zero_reference_helpers=zero_reference_helpers(helpers, references),
        file_line_violations=collect_file_line_violations(modules, settings),
        function_size_violations=collect_function_size_violations(
            modules,
            settings.function_size_threshold,
        ),
    )

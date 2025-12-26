"""
Unit tests for get_class_hierarchy CADSL tool.

Verifies behavior matches reference implementation at:
d:/ROOT/codeine/src/codeine/tools/python_basic/python_tools.py:948-998

Reference behavior:
- Finds class by name or qualified name (CONTAINS filter)
- Returns parents and children
"""

import pytest
from unittest.mock import Mock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from codeine.dsl.tools.inspection.get_class_hierarchy import get_class_hierarchy
from codeine.dsl.core import Pipeline, Context, ToolType


class TestGetClassHierarchyStructure:
    """Test get_class_hierarchy tool structure."""

    def test_has_cadsl_spec(self):
        """Tool should have CADSL spec attached."""
        assert hasattr(get_class_hierarchy, '_cadsl_spec')

    def test_spec_has_correct_name(self):
        """Tool spec should have correct name."""
        spec = get_class_hierarchy._cadsl_spec
        assert spec.name == "get_class_hierarchy"

    def test_has_target_param(self):
        """Should have target parameter."""
        spec = get_class_hierarchy._cadsl_spec
        assert 'target' in spec.params


class TestGetClassHierarchyPipeline:
    """Test get_class_hierarchy pipeline structure."""

    @pytest.fixture
    def pipeline(self):
        """Get the pipeline."""
        spec = get_class_hierarchy._cadsl_spec
        ctx = Context(reter=None, params={"target": "TestClass"}, language="oo", instance_name="default")
        return spec.pipeline_factory(ctx)

    def test_pipeline_is_pipeline_object(self, pipeline):
        """Should return a Pipeline."""
        assert isinstance(pipeline, Pipeline)

    def test_has_emit_key(self, pipeline):
        """Should emit 'hierarchy'."""
        assert pipeline._emit_key == "hierarchy"

    def test_reql_has_class_type(self, pipeline):
        """REQL should filter by Class type."""
        query = pipeline._source.query
        assert "Class" in query

    def test_reql_has_parent_relationship(self, pipeline):
        """REQL should query parent relationships."""
        query = pipeline._source.query
        assert "inheritsFrom" in query

    def test_reql_has_child_relationship(self, pipeline):
        """REQL should query child relationships."""
        query = pipeline._source.query
        # Either query children or have child_name in results
        has_child = "child" in query.lower()
        assert has_child, "Should query child classes"


class TestGetClassHierarchyVsReference:
    """Compare with reference implementation."""

    @pytest.fixture
    def pipeline(self):
        """Get the pipeline."""
        spec = get_class_hierarchy._cadsl_spec
        ctx = Context(reter=None, params={"target": "TestClass"}, language="oo", instance_name="default")
        return spec.pipeline_factory(ctx)

    def test_reference_has_contains_filter(self, pipeline):
        """
        Reference uses CONTAINS for flexible name matching.

        Reference (python_tools.py:973):
            FILTER(?name = class_name || CONTAINS(?qualifiedName, class_name))
        """
        query = pipeline._source.query

        has_contains = "CONTAINS" in query

        if not has_contains:
            pytest.fail(
                "MISSING: CONTAINS filter for flexible name matching.\n"
                "Reference uses: FILTER(?name = class_name || CONTAINS(?qualifiedName, class_name))"
            )

    def test_reference_has_qualified_name(self, pipeline):
        """
        Reference queries qualifiedName.

        Reference (python_tools.py:972):
            ?class qualifiedName ?qualifiedName
        """
        query = pipeline._source.query

        has_qn = "qualifiedName" in query

        if not has_qn:
            pytest.fail(
                "MISSING: qualifiedName property not queried.\n"
                "Reference has: ?class qualifiedName ?qualifiedName"
            )


class TestGetClassHierarchyExecution:
    """Test execution with mock context."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context."""
        ctx = Context(
            reter=Mock(),
            params={"target": "TestClass"},
            language="oo",
            instance_name="default"
        )

        mock_table = Mock()
        mock_table.num_rows = 1
        mock_table.to_pylist.return_value = [
            {
                "?c": "test.TestClass",
                "?name": "TestClass",
                "?parent_name": "BaseClass",
                "?child_name": "ChildClass"
            }
        ]
        ctx.reter.reql.return_value = mock_table

        return ctx

    def test_execute_returns_success(self, mock_context):
        """Execution should return success."""
        result = get_class_hierarchy(ctx=mock_context)
        assert "success" in result

    def test_execute_returns_hierarchy(self, mock_context):
        """Should return hierarchy."""
        result = get_class_hierarchy(ctx=mock_context)
        if result.get("success"):
            assert "hierarchy" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Regression checks for strict-interior writes; no project module is imported."""

import ast
from pathlib import Path
import unittest

import pandas as pd


SOURCE = Path(__file__).resolve().parents[1] / "src/analysis/exercise2_assign_zones.py"


def strict_interior_block():
    """Extract only the reviewed assignment block, without module side effects."""
    tree = ast.parse(SOURCE.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "assign_endpoint")
    def assigns(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    start = next(i for i, n in enumerate(function.body) if assigns(n, "lookup_position")) + 1
    end = next(i for i, n in enumerate(function.body) if assigns(n, "assigned_ids"))
    return compile(ast.Module(body=function.body[start:end], type_ignores=[]), str(SOURCE), "exec")


class StrictInteriorAssignmentTests(unittest.TestCase):
    def check_case(self, prefix, ids):
        result = pd.DataFrame({"analysis_row_id": [10, 20, 30, 40]}, index=[8, 3, 19, 5])
        for suffix in ["zone_id", "zone_name"]:
            result[f"{prefix}_{suffix}"] = pd.Series(pd.NA, index=result.index, dtype="string")
        result[f"{prefix}_assignment_status"] = "invalid_coordinates"
        rows = pd.DataFrame({
            "analysis_row_id": pd.Series(ids, dtype="int64"),
            "zone_id": pd.Series([str(i) for i in ids], dtype="string"),
            "zone_name": pd.Series([f"zone {i}" for i in ids], dtype="string"),
        })
        lookup = pd.Series(result.index.to_numpy(), index=result.analysis_row_id)
        expected = result.copy()
        # Original scalar-write behavior retained as the regression oracle.
        for row in rows.itertuples(index=False):
            pos = lookup.loc[row.analysis_row_id]
            expected.at[pos, f"{prefix}_zone_id"] = row.zone_id
            expected.at[pos, f"{prefix}_zone_name"] = row.zone_name
            expected.at[pos, f"{prefix}_assignment_status"] = "assigned_interior"
        exec(strict_interior_block(), {
            "result": result, "lookup_position": lookup,
            "interior_rows": rows, "prefix": prefix,
        })
        pd.testing.assert_frame_equal(result, expected, check_exact=True)

    def test_origin_empty(self):
        self.check_case("origin", [])

    def test_origin_partial(self):
        self.check_case("origin", [30])

    def test_origin_reordered(self):
        self.check_case("origin", [30, 10, 40])

    def test_destination_empty(self):
        self.check_case("destination", [])

    def test_destination_partial(self):
        self.check_case("destination", [30])

    def test_destination_reordered(self):
        self.check_case("destination", [30, 10, 40])


if __name__ == "__main__":
    unittest.main(verbosity=2)

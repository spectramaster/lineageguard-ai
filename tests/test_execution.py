from pathlib import Path

import pytest

from lineageguard.execution import SafePatchApplier, UnsafePatchError
from lineageguard.models import FilePatch


def test_patch_is_applied_only_inside_root(tmp_path: Path) -> None:
    target = tmp_path / "model.sql"
    target.write_text("select age_years\n", encoding="utf-8")
    patch = FilePatch(
        path="model.sql",
        rationale="compatibility",
        original_text="age_years",
        replacement_text="age_years as customer_age",
    )

    diff = SafePatchApplier(tmp_path).apply(patch)

    assert target.read_text() == "select age_years as customer_age\n"
    assert "+select age_years as customer_age" in diff


def test_patch_path_traversal_is_rejected(tmp_path: Path) -> None:
    patch = FilePatch(
        path="../outside.sql",
        rationale="unsafe",
        original_text="x",
        replacement_text="y",
    )
    with pytest.raises(UnsafePatchError, match="escapes sandbox"):
        SafePatchApplier(tmp_path).apply(patch)


def test_ambiguous_patch_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "model.sql"
    target.write_text("age_years + age_years", encoding="utf-8")
    patch = FilePatch(
        path="model.sql",
        rationale="ambiguous",
        original_text="age_years",
        replacement_text="customer_age",
    )
    with pytest.raises(UnsafePatchError, match="exactly one match"):
        SafePatchApplier(tmp_path).apply(patch)

from __future__ import annotations

import asyncio
import difflib
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from lineageguard.models import FilePatch, RepairPlan, ValidationCheck, ValidationResult


class UnsafePatchError(ValueError):
    """Raised when a generated patch violates the workspace safety policy."""


class SafePatchApplier:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def apply(self, patch: FilePatch) -> str:
        path = (self.root / patch.path).resolve()
        if not path.is_relative_to(self.root):
            raise UnsafePatchError(f"Patch escapes sandbox: {patch.path}")
        if not path.is_file():
            raise UnsafePatchError(f"Patch target is not a file: {patch.path}")
        if patch.original_text is None or patch.replacement_text is None:
            raise UnsafePatchError("Patch must contain exact original and replacement text")

        before = path.read_text(encoding="utf-8")
        occurrences = before.count(patch.original_text)
        if occurrences != 1:
            raise UnsafePatchError(
                f"Expected exactly one match in {patch.path}; found {occurrences}"
            )
        after = before.replace(patch.original_text, patch.replacement_text, 1)
        path.write_text(after, encoding="utf-8")
        return "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{patch.path}",
                tofile=f"b/{patch.path}",
            )
        )


class CommandValidator:
    def __init__(self, timeout_seconds: int = 180) -> None:
        self.timeout_seconds = timeout_seconds

    async def run(self, name: str, command: list[str], cwd: Path) -> ValidationCheck:
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return ValidationCheck(
                name=name,
                command=command,
                passed=False,
                exit_code=124,
                output=f"Timed out after {self.timeout_seconds}s",
                duration_seconds=time.monotonic() - started,
            )
        text = output.decode("utf-8", errors="replace")
        return ValidationCheck(
            name=name,
            command=command,
            passed=process.returncode == 0,
            exit_code=process.returncode or 0,
            output=text[-12_000:],
            duration_seconds=time.monotonic() - started,
        )


class RepairSandbox:
    """Applies generated changes only in a temporary copy, then runs allowlisted checks."""

    def __init__(self, project_root: Path, dbt_executable: Path) -> None:
        self.project_root = project_root.resolve()
        self.dbt_executable = dbt_executable.resolve()

    async def validate(
        self,
        plan: RepairPlan,
        preparation_patches: list[FilePatch] | None = None,
    ) -> tuple[ValidationResult, str]:
        with TemporaryDirectory(prefix="lineageguard-") as temp_dir:
            sandbox = Path(temp_dir) / "project"
            shutil.copytree(
                self.project_root,
                sandbox,
                ignore=shutil.ignore_patterns(
                    ".git", ".venv", ".pytest_cache", ".ruff_cache", "target", "logs"
                ),
            )
            applier = SafePatchApplier(sandbox)
            for preparation in preparation_patches or []:
                applier.apply(preparation)
            diffs = [applier.apply(patch) for patch in plan.patches]

            dbt_root = sandbox / "demo/dbt_project"
            validator = CommandValidator()
            check = await validator.run(
                "dbt build",
                [str(self.dbt_executable), "build", "--profiles-dir", "."],
                dbt_root,
            )
            result = ValidationResult(passed=check.passed, checks=[check])
            return result, "\n".join(diffs)

import argparse
import logging
import subprocess
from pathlib import Path

from src.tools.code_gen import CodeGenTool
from src.core.workflow import ensure_workspace, write_code

logger = logging.getLogger("AutomatedTesting")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class RefinementEngine:
    def __init__(self, api_key: str | None = None, workspace: str = "workshop_dir"):
        self.generator = CodeGenTool(api_key)
        self.workspace = workspace

    def _output_path(self, filename: str = "main.py") -> str:
        return str(Path(self.workspace) / filename)

    def run_tests(self, test_file: str = "tests/test_main.py") -> tuple[bool, str]:
        """Runs pytest and returns a success flag plus output."""
        try:
            result = subprocess.run(
                ["pytest", test_file],
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                return True, "All tests passed."
            return False, output.strip()
        except Exception as e:
            return False, str(e)

    def run_refinement_loop(
        self,
        initial_code: str,
        max_attempts: int = 3,
        output_filename: str = "main.py",
        test_file: str = "tests/test_main.py",
    ) -> str:
        """Save generated code, run pytest, and refine until tests pass or attempts exhaust."""
        current_code = initial_code
        output_path = self._output_path(output_filename)

        ensure_workspace(self.workspace)
        write_code(output_path, current_code)

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Running tests (attempt {attempt}/{max_attempts})...")
            success, feedback = self.run_tests(test_file)
            if success:
                logger.info("Tests passed.")
                return current_code

            logger.warning(f"Tests failed on attempt {attempt}. Feedback:\n{feedback}")
            current_code = self.generator.refine_code(current_code, feedback)
            write_code(output_path, current_code)

        logger.warning("Max refinement attempts reached. Returning latest code.")
        return current_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Run automated tests for generated code.")
    parser.add_argument(
        "--task",
        default="Generate a Python utility that prints system info",
        help="Task description for code generation.",
    )
    parser.add_argument(
        "--output",
        default="main.py",
        help="Output filename inside the workspace.",
    )
    parser.add_argument(
        "--tests",
        default="tests/test_main.py",
        help="Path to the pytest test file.",
    )
    args = parser.parse_args()

    engine = RefinementEngine()
    code = engine.generator.generate(args.task)
    engine.run_refinement_loop(code, output_filename=args.output, test_file=args.tests)


if __name__ == "__main__":
    main()
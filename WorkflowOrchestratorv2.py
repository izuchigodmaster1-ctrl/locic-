import argparse
import subprocess
import os
import logging
from src.tools.code_gen import CodeGenTool
from src.tools.refinement_engine import RefinementEngine
from src.core.workflow import ensure_workspace, sanitize_branch_name, execute_command, write_code

# Setup logging for auditability
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Orchestrator")

class WorkflowOrchestrator:
    def __init__(self, api_key: str):
        self.generator = CodeGenTool(api_key)
        self.refiner = RefinementEngine(api_key)
        self.workspace = "workshop_dir"

    def _execute(self, command: list):
        """Executes a shell command safely."""
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}. Error: {e.stderr}")
            raise

    def _has_staged_changes(self) -> bool:
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode != 0

    def _branch_exists(self, branch_name: str) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", branch_name],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def run_workflow(self, task_description: str):
        logger.info(f"Starting workflow: {task_description}")
        
        ensure_workspace(self.workspace)
        logger.info(f"Using workspace: {self.workspace}")
        branch_name = sanitize_branch_name(task_description)
        
        try:
            # Git operations with error handling
            if self._branch_exists(branch_name):
                logger.info(f"Branch already exists. Checking out {branch_name}.")
                self._execute(["git", "checkout", branch_name])
                branch_created = False
            else:
                self._execute(["git", "checkout", "-b", branch_name])
                branch_created = True
            
            # Integrated Pipeline: Generate -> Refine -> Commit
            code = self.generator.generate(task_description)
            refined_code = self.refiner.run_refinement_loop(code)
            
            # Save and Merge
            output_path = f"{self.workspace}/main.py"
            logger.info(f"Writing generated output to: {output_path}")
            write_code(output_path, refined_code)
            logger.info("Generated code saved.")
            
            self._execute(["git", "add", "."])
            if self._has_staged_changes():
                self._execute(["git", "commit", "-m", f"Implemented {task_description}"])
                self._execute(["git", "checkout", "main"])
                self._execute(["git", "merge", branch_name])
            else:
                logger.info(
                    "No staged changes to commit. Generated output may be ignored by git. "
                    "Skipping commit and merge."
                )
                self._execute(["git", "checkout", "main"])
                if branch_created:
                    self._execute(["git", "branch", "-D", branch_name])
                else:
                    logger.info("Keeping existing branch for future reuse.")
            
            logger.info("Workflow success.")
            
        except Exception as e:
            logger.critical(f"Pipeline crashed: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the locic workflow orchestrator.")
    parser.add_argument("task", help="Task description for code generation.")
    parser.add_argument("--api-key", help="Optional API key for tooling.")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    orchestrator = WorkflowOrchestrator(api_key)
    orchestrator.run_workflow(args.task)


if __name__ == "__main__":
    main()

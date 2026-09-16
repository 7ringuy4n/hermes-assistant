"""Attach capability execution policy from versioned skills, not request prose."""
from pathlib import Path
import json


def delivery_instruction(instruction: str, delivery_binding: dict) -> str:
    """Supply the claimed channel envelope independently of agent classification."""
    binding = {key: delivery_binding.get(key) for key in
               ("thread_id", "thread_type", "source_message_id")}
    if not binding["thread_id"] or not binding["source_message_id"] or binding["thread_type"] not in {"user", "group"}:
        raise ValueError("original delivery binding unavailable")
    return (
        "Original messaging delivery context (not user content): copy this "
        "delivery_binding exactly for any messaging send. Do not infer DM/group "
        "from a numeric ID or replace the original source with a current global turn.\n"
        + json.dumps({"delivery_binding": binding}, ensure_ascii=False)
        + "\n\n" + instruction
    )


def workflow_instruction(instruction: str, task: dict | None, attachments: list | None = None, delivery_binding: dict | None = None, original_request: str | None = None) -> str:
    contract = task if isinstance(task, dict) else {}
    output = str(contract.get("output_type") or contract.get("file_format") or "").lower().lstrip(".")
    kind = str(contract.get("task_type") or "").lower()
    if kind != "file_processing" or output not in {"pdf", "docx", "xlsx", "pptx", "csv", "md", "txt", "image"}:
        return instruction
    asset = Path(__file__).resolve().parents[2] / "skills/file-gen/prompts/execution.txt"
    policy = asset.read_text(encoding="utf-8")
    inputs = attachments if isinstance(attachments, list) else []
    return policy + "\n\n" + json.dumps({"output_type": output,
        "artifact_operation": contract.get("artifact_operation"),
        "original_request": str(original_request or ""),
        "delivery_binding": delivery_binding or {},
        "source_paths": inputs}, ensure_ascii=False) + "\n\n" + instruction

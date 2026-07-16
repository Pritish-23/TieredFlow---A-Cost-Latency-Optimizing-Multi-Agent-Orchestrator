import csv
import io
from datetime import datetime


def export_session_to_csv(call_log: list, session_id: str) -> str:
    """
    Converts a session's call_log into a CSV string.
    Returns the CSV content as a string, ready for st.download_button.
    """
    output = io.StringIO()

    fieldnames = [
        "call_number",
        "timestamp",
        "query_snippet",
        "task_type",
        "tier",
        "model_id",
        "provider",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "latency_ms",
        "served_from_cache",
        "confidence_score",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for entry in call_log:
        row = {field: entry.get(field, "") for field in fieldnames}
        row["task_type"] = str(row["task_type"]).replace("TaskType.", "")
        row["tier"] = str(row["tier"]).replace("Tier.", "")
        writer.writerow(row)

    return output.getvalue()

def export_session_messages_to_csv(messages: list, session_id: str) -> str:
    """
    Converts a list of Message objects (from ConversationStore) into CSV.
    """
    output = io.StringIO()

    fieldnames = [
        "message_id",
        "timestamp",
        "user_query",
        "response",
        "task_type",
        "tier",
        "model_id",
        "cost_usd",
        "latency_ms",
        "served_from_cache",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for msg in messages:
        writer.writerow({
            "message_id": msg.message_id,
            "timestamp": msg.timestamp,
            "user_query": msg.user_query,
            "response": msg.response,
            "task_type": str(msg.task_type).replace("TaskType.", ""),
            "tier": str(msg.tier).replace("Tier.", ""),
            "model_id": msg.model_id,
            "cost_usd": msg.cost_usd,
            "latency_ms": msg.latency_ms,
            "served_from_cache": msg.served_from_cache,
        })

    return output.getvalue()

def export_full_session_report(
    session_id: str,
    call_log: list,
    total_cost: float,
    total_calls: int,
) -> str:
    """
    Generates a fuller CSV with a summary header block followed by the call log.
    """
    output = io.StringIO()

    output.write(f"TieredFlow Session Report\n")
    output.write(f"Session ID,{session_id}\n")
    output.write(f"Generated At,{datetime.now().isoformat()}\n")
    output.write(f"Total Calls,{total_calls}\n")
    output.write(f"Total Cost (USD),{total_cost:.6f}\n")
    output.write("\n")

    csv_body = export_session_to_csv(call_log, session_id)
    output.write(csv_body)

    return output.getvalue()
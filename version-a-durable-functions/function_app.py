import json
import logging
from datetime import timedelta

import azure.functions as func
import azure.durable_functions as df

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}
TIMEOUT_SECONDS = 60
LOCAL_BASE_URL = "http://localhost:7072"


# ------------------------------------------------------
# HTTP STARTER
# ------------------------------------------------------
@app.route(route="expense/start", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_expense_workflow(req: func.HttpRequest, client):
    """
    Starts a new durable orchestration instance for an expense request.
    """
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}, indent=2),
            status_code=400,
            mimetype="application/json"
        )

    instance_id = await client.start_new("expense_approval_orchestrator", None, payload)

    response_body = {
        "message": "Expense workflow started successfully.",
        "instanceId": instance_id,
        "managerActionUrl": f"{LOCAL_BASE_URL}/api/manager/respond/{instance_id}",
        "managerApproveBody": {
            "decision": "approved",
            "managerComment": "Approved by manager"
        },
        "managerRejectBody": {
            "decision": "rejected",
            "managerComment": "Rejected by manager"
        },
        "note": "Save the instanceId. Use managerActionUrl to simulate manager approval or rejection."
    }

    return func.HttpResponse(
        json.dumps(response_body, indent=2),
        status_code=202,
        mimetype="application/json"
    )


# ------------------------------------------------------
# ORCHESTRATOR
# ------------------------------------------------------
@app.orchestration_trigger(context_name="context")
def expense_approval_orchestrator(context: df.DurableOrchestrationContext):
    """
    Orchestrates the expense approval workflow.
    """
    expense = context.get_input()

    # 1. Validate input
    validation_result = yield context.call_activity("validate_expense", expense)

    if not validation_result["is_valid"]:
        final_result = {
            "employee_name": expense.get("employee_name"),
            "employee_email": expense.get("employee_email"),
            "manager_email": expense.get("manager_email"),
            "amount": expense.get("amount"),
            "category": expense.get("category"),
            "description": expense.get("description"),
            "status": "validation_error",
            "approved": False,
            "escalated": False,
            "reason": validation_result["message"]
        }

        yield context.call_activity("send_notification", final_result)
        return final_result

    amount = float(expense["amount"])

    # 2. Auto-approve if under 100
    if amount < 100:
        outcome_input = {
            "expense": expense,
            "status": "approved",
            "approved": True,
            "escalated": False,
            "reason": "Auto-approved because amount is under $100."
        }

        final_result = yield context.call_activity("build_outcome", outcome_input)
        yield context.call_activity("send_notification", final_result)
        return final_result

    # 3. Wait for manager decision or timeout
    deadline = context.current_utc_datetime + timedelta(seconds=TIMEOUT_SECONDS)

    approval_event = context.wait_for_external_event("ManagerDecision")
    timeout_task = context.create_timer(deadline)

    winner = yield context.task_any([approval_event, timeout_task])

    if winner == approval_event:
        manager_response = approval_event.result

        if not timeout_task.is_completed:
            timeout_task.cancel()

        decision = (manager_response.get("decision") or "").strip().lower()

        if decision == "approved":
            outcome_input = {
                "expense": expense,
                "status": "approved",
                "approved": True,
                "escalated": False,
                "reason": "Manager approved the expense.",
                "managerResponse": manager_response
            }
        else:
            outcome_input = {
                "expense": expense,
                "status": "rejected",
                "approved": False,
                "escalated": False,
                "reason": "Manager rejected the expense.",
                "managerResponse": manager_response
            }

        final_result = yield context.call_activity("build_outcome", outcome_input)
        yield context.call_activity("send_notification", final_result)
        return final_result

    # 4. Timeout path -> escalated auto-approval
    outcome_input = {
        "expense": expense,
        "status": "escalated",
        "approved": True,
        "escalated": True,
        "reason": "No manager decision received before timeout. Auto-approved and flagged as escalated."
    }

    final_result = yield context.call_activity("build_outcome", outcome_input)
    yield context.call_activity("send_notification", final_result)
    return final_result


# ------------------------------------------------------
# ACTIVITY: VALIDATION
# ------------------------------------------------------
@app.activity_trigger(input_name="expense")
def validate_expense(expense: dict):
    """
    Validates required fields and category.
    """
    required_fields = [
        "employee_name",
        "employee_email",
        "amount",
        "category",
        "description",
        "manager_email"
    ]

    missing_fields = []
    for field in required_fields:
        value = expense.get(field)
        if value is None or str(value).strip() == "":
            missing_fields.append(field)

    if missing_fields:
        return {
            "is_valid": False,
            "message": f"Missing required field(s): {', '.join(missing_fields)}"
        }

    try:
        amount = float(expense["amount"])
        if amount < 0:
            return {
                "is_valid": False,
                "message": "Amount must be a non-negative number."
            }
    except (TypeError, ValueError):
        return {
            "is_valid": False,
            "message": "Amount must be a valid number."
        }

    category = str(expense["category"]).strip().lower()
    if category not in VALID_CATEGORIES:
        return {
            "is_valid": False,
            "message": f"Invalid category. Valid categories are: {', '.join(sorted(VALID_CATEGORIES))}."
        }

    return {
        "is_valid": True,
        "message": "Validation passed."
    }


# ------------------------------------------------------
# ACTIVITY: BUILD FINAL OUTCOME
# ------------------------------------------------------
@app.activity_trigger(input_name="outcome_data")
def build_outcome(outcome_data: dict):
    """
    Builds the final outcome payload.
    """
    expense = outcome_data["expense"]

    result = {
        "employee_name": expense.get("employee_name"),
        "employee_email": expense.get("employee_email"),
        "manager_email": expense.get("manager_email"),
        "amount": expense.get("amount"),
        "category": expense.get("category"),
        "description": expense.get("description"),
        "status": outcome_data["status"],
        "approved": outcome_data["approved"],
        "escalated": outcome_data["escalated"],
        "reason": outcome_data["reason"]
    }

    if "managerResponse" in outcome_data:
        result["managerResponse"] = outcome_data["managerResponse"]

    return result


# ------------------------------------------------------
# ACTIVITY: SEND NOTIFICATION
# ------------------------------------------------------
@app.activity_trigger(input_name="notification_data")
def send_notification(notification_data: dict):
    """
    Simulates sending a notification email to the employee.
    For this project stage, we log the notification to the console.
    """
    employee_email = notification_data.get("employee_email", "unknown")
    status = notification_data.get("status", "unknown")
    reason = notification_data.get("reason", "")

    logging.info("----- EXPENSE NOTIFICATION -----")
    logging.info("To: %s", employee_email)
    logging.info("Status: %s", status)
    logging.info("Reason: %s", reason)
    logging.info("Full notification payload: %s", json.dumps(notification_data))
    logging.info("--------------------------------")

    return {
        "notification_sent": True,
        "employee_email": employee_email,
        "status": status
    }


# ------------------------------------------------------
# HTTP ENDPOINT: MANAGER RESPONSE
# ------------------------------------------------------
@app.route(route="manager/respond/{instance_id}", methods=["POST"])
@app.durable_client_input(client_name="client")
async def manager_respond(req: func.HttpRequest, client):
    """
    Simulates manager approval or rejection by raising an external event
    to the orchestration instance.
    """
    instance_id = req.route_params.get("instance_id")

    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}, indent=2),
            status_code=400,
            mimetype="application/json"
        )

    decision = (payload.get("decision") or "").strip().lower()
    manager_comment = payload.get("managerComment", "")

    if decision not in {"approved", "rejected"}:
        return func.HttpResponse(
            json.dumps({
                "error": "Decision must be either 'approved' or 'rejected'."
            }, indent=2),
            status_code=400,
            mimetype="application/json"
        )

    event_data = {
        "decision": decision,
        "managerComment": manager_comment
    }

    try:
        await client.raise_event(instance_id, "ManagerDecision", event_data)
    except Exception as ex:
        return func.HttpResponse(
            json.dumps({
                "error": "Unable to deliver manager decision.",
                "details": str(ex),
                "instanceId": instance_id
            }, indent=2),
            status_code=409,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({
            "message": f"Manager decision '{decision}' sent successfully.",
            "instanceId": instance_id,
            "eventData": event_data
        }, indent=2),
        status_code=200,
        mimetype="application/json"
    )
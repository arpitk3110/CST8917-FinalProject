import json
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}


@app.route(route="", methods=["POST"])
def validate_expense(req: func.HttpRequest) -> func.HttpResponse:
    try:
        expense = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({
                "is_valid": False,
                "message": "Request body must be valid JSON."
            }, indent=2),
            status_code=400,
            mimetype="application/json"
        )

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
        return func.HttpResponse(
            json.dumps({
                "is_valid": False,
                "message": f"Missing required field(s): {', '.join(missing_fields)}"
            }, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    try:
        amount = float(expense["amount"])
        if amount < 0:
            return func.HttpResponse(
                json.dumps({
                    "is_valid": False,
                    "message": "Amount must be a non-negative number."
                }, indent=2),
                status_code=200,
                mimetype="application/json"
            )
    except (TypeError, ValueError):
        return func.HttpResponse(
            json.dumps({
                "is_valid": False,
                "message": "Amount must be a valid number."
            }, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    category = str(expense["category"]).strip().lower()
    if category not in VALID_CATEGORIES:
        return func.HttpResponse(
            json.dumps({
                "is_valid": False,
                "message": f"Invalid category. Valid categories are: {', '.join(sorted(VALID_CATEGORIES))}."
            }, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({
            "is_valid": True,
            "message": "Validation passed."
        }, indent=2),
        status_code=200,
        mimetype="application/json"
    )
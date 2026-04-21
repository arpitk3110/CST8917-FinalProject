# Expense Processing System – Serverless Final Project

**Name:** Arpit Patel  

**Student Number:** 041159097  

**Course Code:** CST8917 Serverless Applications

**Project Title:** Expense Approval Workflow 

**Date:** 21st April 2026


# Expense Approval Workflow – Version A (Azure Durable Functions)

## Overview

This project implements an **expense approval workflow** using Azure Durable Functions. The system processes employee expense requests and applies business rules such as validation, automatic approval, manager decision handling, and timeout-based escalation.

The workflow is designed to simulate a real-world approval system where expenses are evaluated based on predefined rules and human interaction.

---

## Workflow Logic

The workflow follows these steps:

1. The employee submits an expense request via an HTTP endpoint.
2. The system validates the request (required fields and category).
3. Based on the amount:

   * If **less than $100** → automatically approved.
   * If **greater than or equal to $100** → waits for manager decision.
4. If the manager:

   * Approves → expense is approved.
   * Rejects → expense is rejected.
5. If no response is received within the timeout period → expense is **auto-approved and escalated**.

---

## Technologies Used

* Azure Durable Functions (Python)
* Azure Functions Core Tools
* VS Code (REST Client extension)
* Python 3.12

---

## How to Run Locally

### 1. Activate virtual environment

```bash
.venv\Scripts\activate
```

### 2. Start the function app

```bash
func start --port 7072
```

### 3. Test scenarios

Use the `test-durable.http` file to run all test cases.

---

## Test Scenarios and Expected Results

| Scenario   | Input Condition                  | Expected Result        |
| ---------- | -------------------------------- | ---------------------- |
| Scenario 1 | Amount < $100                    | Approved automatically |
| Scenario 2 | Amount ≥ $100 + manager approves | Approved               |
| Scenario 3 | Amount ≥ $100 + manager rejects  | Rejected               |
| Scenario 4 | Amount ≥ $100 + no response      | Escalated              |
| Scenario 5 | Missing required fields          | Validation error       |
| Scenario 6 | Invalid category                 | Validation error       |

---

## Key Features

* Durable orchestration using Azure Durable Functions
* Input validation for required fields and categories
* Automatic approval logic for small expenses
* External event handling for manager decisions
* Timeout handling using durable timers
* Escalation mechanism for delayed approvals

---





## Conclusion

This implementation demonstrates how Durable Functions can be used to manage complex workflows involving validation, human interaction, and time-based events. The system successfully handles all required scenarios and reflects real-world business logic for expense approvals.

## Part 2: Version B — Logic Apps + Service Bus

### Overview

In this part, I implemented an event-driven expense processing system using Azure Logic Apps and Azure Service Bus. The workflow receives expense requests from a Service Bus queue, validates them using an Azure Function, applies business rules, and sends notifications via email.

This version focuses on orchestration using Logic Apps instead of code-based orchestration (as in Version A), making it easier to visualize and manage the workflow.

---

### Architecture Components

The system consists of the following components:

- **Azure Service Bus (Queue)** – Receives incoming expense requests  
- **Azure Logic App** – Orchestrates the workflow and decision logic  
- **Azure Function** – Performs validation of incoming requests  
- **Outlook Email Connector** – Sends notifications to employee and manager  

---

### Implementation Steps

#### Step 1: Service Bus Queue Setup

A queue named `expense-requests` was created in Azure Service Bus. This queue is used to receive incoming expense requests in JSON format.

---

#### Step 2: Logic App Creation

A Logic App (Consumption plan) was created and configured using the Logic App Designer. This serves as the main orchestration layer for the workflow.

---

#### Step 3: Trigger Configuration

The workflow starts with the trigger:

When a message is received in a queue (auto-complete)

This trigger listens to the `expense-requests` queue and processes each incoming message automatically.

---

#### Step 4: Parse Incoming Request

The incoming message from Service Bus is parsed using a **Parse JSON** action. This extracts fields such as:

- employee_name  
- employee_email  
- amount  
- category  
- description  
- manager_email  

---

#### Step 5: Validation Using Azure Function

The parsed request is sent to an Azure Function (`validate-expense`) which performs validation checks such as:

- Missing required fields  
- Invalid category  
- Invalid or negative amount  

The function returns a response with:

is_valid (true/false)
message (validation result)


---

#### Step 6: Parse Validation Response

Another Parse JSON action is used to extract the `is_valid` and `message` fields from the function response.

---

#### Step 7: Initialize Workflow Variables

The following variables are initialized to manage workflow decisions:

- finalStatus (String)  
- approved (Boolean)  
- escalated (Boolean)  
- reason (String)  

---

#### Step 8: Validation Condition

A condition checks:

is_valid == true


- If **false**, a validation error email is sent to the employee  
- If **true**, the workflow continues to decision logic  

---

#### Step 9: Auto-Approval Logic

Another condition checks:

amount < 100


If true:
- The request is auto-approved  
- Variables are set:
  - finalStatus = "Approved"  
  - approved = true  
  - escalated = false  
  - reason = "Auto-approved because amount is under $100."  

---

#### Step 10: Manager Review Logic

If amount is greater than or equal to 100:

1. An email is sent to the manager requesting review  
2. A condition checks:

amount == 300


- If true:
  - Request is rejected  
  - finalStatus = "Rejected"  

- If false:
  - Request is escalated  
  - finalStatus = "Escalated"  
  - approved = true  
  - escalated = true  
  - reason = "No manager decision received before timeout. Auto-approved and flagged as escalated."  

---

#### Step 11: Send Outcome to Service Bus

The final result is sent to a Service Bus destination (`expense-outcomes`) with the following structure:

{
employee details,
status,
approved,
escalated,
reason
}


Content type is set to `application/json`.

---

#### Step 12: Final Notification to Employee

A final email is sent to the employee with the result:

- Status  
- Approval result  
- Escalation status  
- Reason  

---

### Testing

The workflow was tested using Service Bus Explorer with different input scenarios.

#### Scenario 1: Auto Approval

amount = 75

- Result: Approved  
- Email sent to employee  

#### Scenario 2: Manager Review / Escalation

amount = 175

- Manager email sent  
- Final status: Escalated  

#### Scenario 3: Validation Error
- Missing or invalid fields  
- Validation error email sent  

---

### Observations

- Logic Apps provided a clear visual workflow for decision-making  
- Azure Function ensured clean and reusable validation logic  
- Email notifications worked correctly for all scenarios  
- Service Bus successfully handled input and output messages  
- The system behaves as expected for auto-approval, escalation, and validation cases  

---

### Conclusion

This implementation demonstrates how Azure Logic Apps and Service Bus can be combined to build a scalable and event-driven workflow. Logic Apps handled orchestration, while Azure Functions handled validation logic. The overall system is easy to maintain, monitor, and extend, making it suitable for real-world cloud-based applications.





## Part 3: Comparison Analysis

This section presents a structured comparison between the Logic App-based workflow and the Azure Function-based validation used in this project. The comparison is based on actual implementation experience and focuses on development, testing, error handling, human interaction, observability, and cost. Both approaches were used together in this project, which provided a clear understanding of their strengths and limitations in a real-world scenario.

---

### 1. Development Experience

The Logic App approach was significantly faster to build compared to the Azure Function-based implementation. Using the visual designer, I was able to connect Service Bus, conditions, variables, and email actions without writing much code. This made it easier to quickly implement the workflow and understand the overall process. The drag-and-drop interface also helped in visualizing the complete flow, which reduced confusion during development.

However, debugging in Logic Apps required checking the run history step-by-step, which sometimes took extra time, especially when multiple nested conditions were involved. In contrast, the Azure Function required writing Python code for validation, which took more effort initially. Despite that, it provided better control over logic and structure. Errors were easier to identify through logs, and the code-based approach allowed more precise handling of validation rules.

Overall, Logic Apps were faster to develop and easier for workflow creation, while Azure Functions provided more confidence in the correctness and flexibility of the logic.

---

### 2. Testability

Testing the Logic App workflow was easier for end-to-end scenarios. I could send messages directly to the Service Bus queue and observe how the entire workflow executed through the run history. This made it simple to test real scenarios such as auto-approval for small amounts, escalation for higher amounts, and validation failures. The visual feedback provided immediate confirmation of how the system behaved.

On the other hand, Azure Functions were easier to test locally. I was able to test different inputs using local execution, which helped in validating edge cases such as missing fields, invalid values, or incorrect data types. Automated testing is also more practical with Azure Functions since they are code-based and can be integrated with testing frameworks.

In summary, Logic Apps are better suited for integration and workflow testing, while Azure Functions are more effective for local testing and automated validation of logic.

---

### 3. Error Handling

Error handling in Azure Functions was more controlled and explicit. I implemented validation checks in Python and returned structured error responses for cases like missing fields, invalid categories, or incorrect data types. This allowed precise control over how errors were handled and ensured that meaningful feedback was returned to the Logic App.

In Logic Apps, error handling was implemented using conditional branches. Invalid requests were routed to a separate path that triggered validation error emails. Additionally, Logic Apps provide built-in retry policies and failure tracking, which are useful for handling temporary issues such as service interruptions. However, configuring error paths required careful setup to avoid workflow failures.

Overall, Azure Functions provided more control and flexibility for handling errors at the code level, while Logic Apps made it easier to visualize and manage error flows within the workflow.

---

### 4. Human Interaction Pattern

Handling human interaction, such as waiting for manager approval, was more natural in Logic Apps. The visual workflow made it easy to represent decision points, branching logic, and escalation conditions. For example, when the expense amount exceeded a threshold, the system sent an email to the manager and followed a review process.

If no action was taken within a certain time, the request was automatically escalated. This type of time-based and event-driven workflow is difficult to implement purely in Azure Functions without additional orchestration services such as Durable Functions.

Logic Apps are designed specifically for workflows involving approvals, delays, and human interaction. This made the implementation more intuitive and easier to manage compared to a purely code-based approach.

---

### 5. Observability

Logic Apps provided strong observability through the run history feature. Each step of the workflow could be inspected in detail, including inputs, outputs, execution time, and errors. This made it very easy to debug issues and understand how data was flowing through the system. The visual representation also helped in identifying exactly where failures occurred.

In contrast, Azure Functions relied on logs and Application Insights for monitoring. While these tools are powerful and provide detailed insights, they require more effort to interpret, especially for beginners. It is not as visually intuitive as Logic Apps.

Based on my experience, Logic Apps made it easier to monitor executions, track errors, and diagnose problems quickly, especially during development and testing phases.

---

### 6. Cost

For low usage scenarios, such as around 100 expense requests per day, both Logic Apps and Azure Functions are cost-effective. Logic Apps charge per action execution, and since this workflow includes multiple steps (conditions, variables, emails, etc.), the cost increases slightly with complexity. However, for small-scale usage, the cost remains minimal and manageable.

For higher usage scenarios, such as around 10,000 requests per day, Azure Functions become more cost-efficient. Functions are billed based on execution time and resource consumption, which makes them more scalable for large workloads. Logic Apps, on the other hand, can become more expensive due to per-action pricing.

Therefore, Logic Apps are suitable for low to moderate workloads and quick development, while Azure Functions are more economical and scalable for high-volume processing.

---

### Recommendation

Based on my implementation experience, I would choose Logic Apps for production in scenarios where the system primarily involves workflow orchestration, service integration, and human interaction such as approvals. The visual designer made it easy to build and understand the workflow, especially when dealing with multiple conditions, branching logic, and email notifications. It significantly reduced development time and helped in quickly identifying issues using the run history feature. For business processes that require clear visibility and minimal coding, Logic Apps provide a very efficient and maintainable solution.

However, I would choose Azure Functions when the system requires complex business logic, custom validation, or high-performance processing. Functions offer more flexibility because they are code-based, allowing better control over logic, structured error handling, and easier integration with automated testing frameworks. They are also more suitable for scaling large workloads and optimizing cost when handling high volumes of requests.

In this project, combining Azure Functions for validation and Logic Apps for orchestration proved to be the most effective approach. Logic Apps handled the workflow execution, communication, and decision-making process, while Azure Functions ensured accurate and reusable validation logic. This hybrid architecture reflects real-world cloud design patterns and provides a balanced solution that is both scalable and easy to maintain.

## References

Microsoft. (n.d.). *Azure Logic Apps documentation*.  
https://learn.microsoft.com/en-us/azure/logic-apps/

Microsoft. (n.d.). *Azure Service Bus Messaging documentation*.  
https://learn.microsoft.com/en-us/azure/service-bus-messaging/

Microsoft. (n.d.). *Azure Functions documentation*.  
https://learn.microsoft.com/en-us/azure/azure-functions/

Microsoft. (n.d.). *Call Azure Functions from workflows in Azure Logic Apps*.  
https://learn.microsoft.com/en-us/azure/logic-apps/call-azure-functions-from-workflows

Microsoft. (n.d.). *Service Bus triggers and bindings for Azure Functions*.  
https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-service-bus

Microsoft. (n.d.). *Azure Logic Apps connectors overview*.  
https://learn.microsoft.com/en-us/azure/connectors/apis-list

Microsoft. (n.d.). *Azure pricing overview*.  
https://azure.microsoft.com/en-us/pricing/

Microsoft. (n.d.). *Monitor Azure Logic Apps*.  
https://learn.microsoft.com/en-us/azure/logic-apps/monitor-logic-apps

Microsoft. (n.d.). *Monitor executions in Azure Functions*.  
https://learn.microsoft.com/en-us/azure/azure-functions/functions-monitoring

## AI Disclosure

AI tools were used during this project to assist with understanding Azure services, code generation, debugging issues, and improving documentation clarity.  
All core implementation, configuration, and testing were performed independently based on course requirements.  
AI-generated suggestions were reviewed, modified, and validated before being applied to the project.  
The final solution reflects my own understanding and hands-on work with Azure Logic Apps, Service Bus, and Functions.


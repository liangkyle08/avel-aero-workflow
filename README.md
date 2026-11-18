# Avel Aero Charter Workflow Engine

A small command-line workflow engine built in Python for the Avel Aero engineering internship technical assessment.

The program simulates a fictional charter inquiry from aircraft availability through quote preparation and human approval. It uses mocked services only. It does not contact an aircraft provider, send an email, or call an external API.

## Assessment requirements covered

| Assessment requirement | Where it is implemented |
| --- | --- |
| Execute four steps in order | `WorkflowEngine.run()` |
| Pass results between steps | `self.results` stores availability data and the prepared quote |
| Simulate a tool failure | `AvailabilityTool.check()` raises a timeout on its first call |
| Retry or recover from failure | `WorkflowEngine.check_availability()` retries up to `max_attempts` |
| Pause before sending | The engine enters `PAUSED` and calls the approval callback before sending |
| Require explicit human approval | The CLI callback accepts only the response `yes` |
| Track status and readable history | `WorkflowStatus`, `HistoryEvent`, and `WorkflowEngine.history` |
| Keep outside services mocked | `AvailabilityTool` and `MockSendService` return local, fictional data |

## Requirements

- Python 3.9 or newer
- No third-party Python packages

The project uses only Python's standard library.

## Project structure

```text
avel-aero-workflow/
├── main.py
├── README.md
├── .gitignore
└── tests/
    └── test_workflow.py
```

### `main.py`

Contains the workflow engine and the mocked services.

- `WorkflowStatus` defines the overall workflow states.
- `HistoryEvent` stores a timestamped history message.
- `AvailabilityTool` simulates an aircraft availability service. Its first call raises a timeout, and its next call succeeds.
- `QuoteService` prepares a quote using the inquiry and availability result.
- `MockSendService` simulates sending an approved quote. It does not send a real message.
- `WorkflowEngine` runs the steps in order, handles retries, pauses for approval, and records history.
- `request_human_approval()` displays the draft and asks the user to approve it.
- `main()` creates a sample inquiry and starts the command-line program.

### `tests/test_workflow.py`

Contains automated tests for the successful path, the retry behavior, and the approval gate. The tests use Python's built-in `unittest` module.

## How to run

### 1. Clone the repository

After uploading this project to GitHub, clone it:

```bash
git clone <your-github-repository-url>
cd avel-aero-workflow
```

Replace `<your-github-repository-url>` with the URL of your repository.

### 2. Run the workflow

```bash
python main.py
```

On some systems, use `python3 main.py` instead.

The program will:

1. Start workflow `REQ-1042`.
2. Attempt to check aircraft availability.
3. Simulate a temporary timeout on the first attempt.
4. Retry the availability check and receive mock aircraft data.
5. Prepare a quote.
6. Display the quote and pause for approval.
7. Wait for your response.
8. Send the quote only if you type `yes`.
9. Print the timestamped execution history and final status.

When prompted, type `yes` to approve. Any other response rejects the quote and prevents the send step.

### 3. Run the automated tests

```bash
python -m unittest discover -s tests -v
```

The tests do not require network access or third-party packages.

## Example execution

The exact timestamps will differ. The approval prompt is interactive, so the example below shows the expected successful path.

```text
Quote awaiting approval:
  Reference: REQ-1042
  Route: San Francisco to Los Angeles
  Date: 2026-12-10
  Aircraft: Citation XLS
  Price: $12,500
  Status: Draft

Approve this quote? Type 'yes' to approve: yes

Execution history:
[time] START: Workflow REQ-1042
[time] RUNNING: Check availability (attempt 1)
[time] FAILED: Temporary API timeout
[time] RETRY: Attempt 2
[time] RUNNING: Check availability (attempt 2)
[time] SUCCESS: Aircraft availability received
[time] RUNNING: Prepare quote
[time] SUCCESS: Draft prepared
[time] PAUSED: Waiting for human approval
[time] APPROVED: Human approved draft
[time] RUNNING: Send quote (mock)
[time] SUCCESS: Mock send completed for quote REQ-1042.
[time] COMPLETE: Workflow finished

Final workflow status: COMPLETE
```

If you type anything other than `yes`, the workflow ends with `REJECTED`. The send step is not called.

## Architecture

The design uses a small object-oriented structure. Each service has one responsibility, while `WorkflowEngine` coordinates the services and controls the order of execution.

```text
                 WorkflowEngine
                       |
          +------------+-------------+
          |            |             |
   AvailabilityTool  QuoteService  MockSendService
          |            |             |
       Result ------> Quote ------> Mock result
                       |
                Human approval
                       |
                 Send or reject
```

The workflow passes ordinary Python dictionaries between steps. This keeps the example easy to read and avoids introducing a database or a more complex messaging system.

## Key design decision: approval is a hard gate

The send operation is placed after the approval callback. The engine does not call `MockSendService.send()` until the callback returns `True`.

This is important because a workflow that merely logs that approval is needed is not enough. The execution order itself must prevent the sensitive action from happening early.

The CLI callback treats only the exact response `yes` as approval. The tests also check that a rejected workflow never starts the send step.

## Failure handling

The availability tool intentionally fails on its first call with `TimeoutError("Temporary API timeout")`.

`check_availability()` catches that error, records it, and retries. The retry limit is configurable through `max_attempts`, which defaults to two in this project.

If every attempt fails, the error is passed back to the workflow runner. The runner marks the workflow `FAILED` and records the reason. The retry loop is bounded, so it cannot run forever.

## Limitations and possible improvements

This is an assessment-sized demonstration, not a production workflow platform.

- **In-memory state:** History and results disappear when the process exits. A production system would persist workflow state.
- **Single-process execution:** There is no queue or background worker, so the program handles one workflow at a time.
- **Simple retry policy:** The retry is immediate and has a fixed attempt limit. A production system could use exponential backoff and distinguish retryable from permanent errors.
- **Mock services:** Aircraft availability, pricing, and sending are fictional. No real service is contacted.
- **Basic approval identity:** The CLI records an approval decision but does not authenticate the person making it. A real system would need access controls and an auditable approver identity.

## Design scope

The assessment asks for a small execution engine and explicitly allows a CLI program, hardcoded tool responses, and simulated failures. This project intentionally avoids a frontend, database, actual LLM, deployment, phone integration, authentication, and paid APIs.

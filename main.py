"""Run a mocked charter-inquiry workflow from the command line."""

from dataclasses import dataclass, field  # Store structured workflow data.
from datetime import datetime  # Timestamp each history event.
from enum import Enum  # Keep workflow states consistent.
from typing import Callable, Dict, List, Optional  # Describe callback and data types.


class WorkflowStatus(str, Enum):
    """Possible overall states for a workflow."""

    PENDING = "PENDING"  # The workflow has not started.
    RUNNING = "RUNNING"  # A workflow step is executing.
    PAUSED = "PAUSED"  # The workflow is waiting for human approval.
    REJECTED = "REJECTED"  # A human declined the quote.
    FAILED = "FAILED"  # The workflow stopped because a step failed.
    COMPLETE = "COMPLETE"  # Every required step finished successfully.


@dataclass
class HistoryEvent:
    """One readable event in the workflow execution history."""

    message: str  # Describe what happened.
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))  # Record when it happened.

    def __str__(self) -> str:
        """Format an event for the terminal."""
        return f"[{self.timestamp}] {self.message}"  # Show the time beside the event.


class AvailabilityTool:
    """Mock aircraft availability and fail once to demonstrate recovery."""

    def __init__(self) -> None:
        self.has_failed = False  # Remember whether the simulated timeout occurred.

    def check(self, inquiry: Dict[str, str]) -> Dict[str, str]:
        """Return mock aircraft data after one intentional timeout."""
        if not self.has_failed:  # Trigger the failure only on the first call.
            self.has_failed = True  # Ensure the next attempt can succeed.
            raise TimeoutError("Temporary API timeout")  # Simulate an unavailable service.

        return {  # Return mock data for the quote step.
            "aircraft": "Citation XLS",  # Provide a fictional aircraft type.
            "availability": "Available",  # State the mock availability result.
            "route": f"{inquiry['origin']} to {inquiry['destination']}",  # Carry inquiry details forward.
            "date": inquiry["date"],  # Preserve the requested travel date.
        }


class QuoteService:
    """Prepare a quote from the inquiry and availability result."""

    def prepare(self, inquiry: Dict[str, str], availability: Dict[str, str]) -> Dict[str, str]:
        """Build a fictional quote without contacting an external service."""
        return {  # Return the quote as structured data.
            "reference": inquiry["reference"],  # Keep the inquiry reference.
            "route": availability["route"],  # Use the route confirmed by availability.
            "date": availability["date"],  # Use the date returned by availability.
            "aircraft": availability["aircraft"],  # Include the selected aircraft.
            "price": "$12,500",  # Use a fixed fictional price.
            "status": "Draft",  # Mark the quote as a draft until approved.
        }


class MockSendService:
    """Pretend to send a quote without sending a real message."""

    def send(self, quote: Dict[str, str]) -> str:
        """Return a confirmation string for the approved quote."""
        return f"Mock send completed for quote {quote['reference']}."  # Confirm the simulated action.


class WorkflowEngine:
    """Coordinate the four workflow steps and record every important event."""

    def __init__(self, max_attempts: int = 2) -> None:
        self.max_attempts = max_attempts  # Limit retries so failures cannot loop forever.
        self.status = WorkflowStatus.PENDING  # Start in the pending state.
        self.history: List[HistoryEvent] = []  # Keep an ordered execution log.
        self.availability_tool = AvailabilityTool()  # Create the mocked availability tool.
        self.quote_service = QuoteService()  # Create the quote preparation service.
        self.send_service = MockSendService()  # Create the mocked send service.
        self.results: Dict[str, Dict[str, str]] = {}  # Share step results with later steps.

    def record(self, message: str) -> None:
        """Add one event to the execution history."""
        self.history.append(HistoryEvent(message))  # Preserve events in execution order.

    def check_availability(self, inquiry: Dict[str, str]) -> Dict[str, str]:
        """Retry availability checks when a temporary error occurs."""
        for attempt in range(1, self.max_attempts + 1):  # Try no more than the configured limit.
            self.record(f"RUNNING: Check availability (attempt {attempt})")  # Record the attempt.
            try:  # Handle temporary service errors.
                result = self.availability_tool.check(inquiry)  # Call the mocked availability tool.
                self.record("SUCCESS: Aircraft availability received")  # Record successful completion.
                return result  # Pass the result to the quote step.
            except TimeoutError as error:  # Catch the simulated timeout.
                self.record(f"FAILED: {error}")  # Make the failure visible in the history.
                if attempt < self.max_attempts:  # Retry only when another attempt is allowed.
                    self.record(f"RETRY: Attempt {attempt + 1}")  # Explain the recovery action.
                else:  # Stop when the retry limit is reached.
                    raise  # Let the workflow mark itself as failed.
        raise RuntimeError("Availability check ended unexpectedly.")  # Guard against an impossible fall-through.

    def run(self, inquiry: Dict[str, str], approval_callback: Callable[[Dict[str, str]], bool]) -> WorkflowStatus:
        """Execute the workflow and request approval before the mock send."""
        self.status = WorkflowStatus.RUNNING  # Mark the workflow as active.
        self.record(f"START: Workflow {inquiry['reference']}")  # Record the workflow start.

        try:  # Convert unexpected step errors into a clear failed workflow state.
            self.results["availability"] = self.check_availability(inquiry)  # Step 1: check aircraft availability.
            self.record("RUNNING: Prepare quote")  # Record the start of step 2.
            self.results["quote"] = self.quote_service.prepare(inquiry, self.results["availability"])  # Step 2: prepare quote.
            self.record("SUCCESS: Draft prepared")  # Record the completed draft.

            self.status = WorkflowStatus.PAUSED  # Pause before any sending action.
            self.record("PAUSED: Waiting for human approval")  # Make the approval gate explicit.
            approved = approval_callback(self.results["quote"])  # Ask a human or test callback for a decision.

            if not approved:  # Never send a quote after a rejection.
                self.status = WorkflowStatus.REJECTED  # Mark the workflow as rejected.
                self.record("REJECTED: Human declined the draft")  # Record the human decision.
                return self.status  # Stop before the send step.

            self.results["quote"]["status"] = "Approved"  # Mark the draft approved before sending.
            self.record("APPROVED: Human approved draft")  # Record explicit approval.
            self.record("RUNNING: Send quote (mock)")  # Record the start of step 4.
            send_result = self.send_service.send(self.results["quote"])  # Step 4: perform a mocked send.
            self.record(f"SUCCESS: {send_result}")  # Record the mock send result.

            self.status = WorkflowStatus.COMPLETE  # Mark all workflow steps as complete.
            self.record("COMPLETE: Workflow finished")  # Record the final state.
            return self.status  # Return the final workflow status.
        except Exception as error:  # Catch errors that prevent workflow completion.
            self.status = WorkflowStatus.FAILED  # Mark the workflow as failed.
            self.record(f"FAILED: Workflow stopped: {error}")  # Preserve the reason for failure.
            return self.status  # Return failure rather than hiding it.

    def print_history(self) -> None:
        """Print the workflow history in chronological order."""
        print("\nExecution history:")  # Label the history section.
        for event in self.history:  # Visit each recorded event.
            print(event)  # Display the event and timestamp.


def request_human_approval(quote: Dict[str, str]) -> bool:
    """Display the draft and require an explicit yes before sending."""
    print("\nQuote awaiting approval:")  # Identify the approval checkpoint.
    for key, value in quote.items():  # Show every quote field.
        print(f"  {key.title()}: {value}")  # Display the field in a readable format.
    answer = input("\nApprove this quote? Type 'yes' to approve: ").strip().lower()  # Read the human decision.
    return answer == "yes"  # Approve only the exact affirmative response.


def main() -> None:
    """Create a sample inquiry and run the command-line workflow."""
    inquiry = {  # Use fictional charter inquiry details.
        "reference": "REQ-1042",  # Identify this workflow run.
        "origin": "San Francisco",  # Set the fictional departure city.
        "destination": "Los Angeles",  # Set the fictional destination city.
        "date": "2026-12-10",  # Set a fictional travel date.
    }
    engine = WorkflowEngine(max_attempts=2)  # Allow one retry after the simulated timeout.
    final_status = engine.run(inquiry, request_human_approval)  # Execute and pause for human input.
    engine.print_history()  # Show the complete execution record.
    print(f"\nFinal workflow status: {final_status.value}")  # Summarize the outcome.


if __name__ == "__main__":  # Run the CLI only when this file is executed directly.
    main()  # Start the application.

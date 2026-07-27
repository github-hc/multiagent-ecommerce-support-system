from typing import TypedDict, Optional


class TicketState(TypedDict):
    ticket_id: str
    customer_id: str
    order_id: Optional[str]
    subject: Optional[str]
    body: str

    # filled in by Triage
    category: Optional[str]
    priority: Optional[str]

    # filled in by later agents (Step 11+)
    kb_results: list
    draft_response: Optional[str]
    qa_feedback: Optional[str]
    qa_approved: bool
    iteration_count: int
    requires_human_approval: bool
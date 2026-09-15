from typing import List, Dict, Any
from src.data_processing.schemas import Order

class InfeasibilityPolicy:
    """
    Implements Option 2: Flag the order as unassignable and surface it explicitly to the manager.
    Silence is not acceptable. Any order that fundamentally violates time windows or capacity 
    will not be silently penalized or patched into a route; it will be formally excluded 
    and added to this unassigned tracker with a specific reason string.
    """
    def __init__(self):
        self.unassigned_orders: List[Dict[str, Any]] = []

    def record_unassigned(self, order: Order, reason: str):
        """
        Records an order that could not be feasibly assigned into any route.
        """
        self.unassigned_orders.append({
            "order": order,
            "reason": reason
        })

    def get_report(self) -> List[Dict[str, Any]]:
        """
        Returns a machine-readable list of unassigned/violating orders with reasons,
        ready for the Phase 5 UI to render.
        """
        return self.unassigned_orders

    def clear(self):
        self.unassigned_orders.clear()

# Global singleton tracker for a given routing session
infeasibility_tracker = InfeasibilityPolicy()

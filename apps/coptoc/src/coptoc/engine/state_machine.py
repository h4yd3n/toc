from typing import Tuple
from shared.models import VisibilityState


class VisibilityStateMachine:
    """
    Manages valid state transitions between [visible, limited, held, removed].
    Prevents unauthorized state escalations or invalid loops.
    """

    ALLOWED_TRANSITIONS = {
        VisibilityState.VISIBLE: {VisibilityState.LIMITED, VisibilityState.HELD, VisibilityState.REMOVED},
        VisibilityState.LIMITED: {VisibilityState.VISIBLE, VisibilityState.HELD, VisibilityState.REMOVED},
        VisibilityState.HELD: {VisibilityState.VISIBLE, VisibilityState.LIMITED, VisibilityState.REMOVED},
        VisibilityState.REMOVED: {VisibilityState.VISIBLE, VisibilityState.LIMITED}, # Only via successful human appeal
    }

    @classmethod
    def can_transition(cls, current: VisibilityState, target: VisibilityState) -> bool:
        if current == target:
            return True
        return target in cls.ALLOWED_TRANSITIONS.get(current, set())

    @classmethod
    def transition(
        cls, current: VisibilityState, target: VisibilityState
    ) -> Tuple[VisibilityState, bool]:
        if cls.can_transition(current, target):
            return target, True
        return current, False

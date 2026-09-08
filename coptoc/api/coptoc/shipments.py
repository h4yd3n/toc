"""Canonical shipment writes shared by manual entry and reviewed intake proposals.

Callers own authorization and transaction boundaries. These helpers never commit.
"""
from datetime import datetime
from sqlalchemy import update
from .sections import ShipmentRow


def add_shipment(session, *, record_id, **values):
    row = ShipmentRow(id=record_id, **values)
    session.add(row)
    return row


async def patch_shipment(session, record_id, values, expected=None):
    predicates = [ShipmentRow.id == record_id]
    for key, value in (expected or {}).items():
        if key in ('eta', 'updated_at') and value:
            value = datetime.fromisoformat(value)
        predicates.append(getattr(ShipmentRow, key) == value)
    result = await session.execute(update(ShipmentRow).where(*predicates).values(**values))
    return result.rowcount == 1

"""Deterministic administrative checks; no provider calls or automatic record changes."""
import hashlib
import json
from datetime import timedelta
from fastapi import Depends, HTTPException
from pydantic import Field
from sqlalchemy import DateTime, Integer, String, Text, select, update
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base
from sigtoc.work import now, StrictModel, session_dep, request_actor, scope_ok
from .sections import ShipmentRow
from .ingestion import router, access


class MonitorRow(Base):
    __tablename__ = 'cop_administrative_monitor'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    shipment_id: Mapped[str] = mapped_column(String, unique=True)
    location_id: Mapped[str] = mapped_column(String)
    fingerprint: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default='open')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    checked_at: Mapped[object] = mapped_column(DateTime)
    snoozed_until: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    history_json: Mapped[str] = mapped_column(Text, default='[]')


class MonitorDecision(StrictModel):
    revision: int
    action: str = Field(pattern='^(dismiss|snooze|reopen)$')
    note: str = Field(min_length=1, max_length=1000)


async def monitor_tick():
    from sigtoc.api import sessions
    async with sessions()() as session:
        stamp = now()
        shipments = (await session.scalars(select(ShipmentRow))).all()
        checks = {r.shipment_id:r for r in (await session.scalars(select(MonitorRow))).all()}
        for shipment in shipments:
            if not shipment.to_location_id:
                continue
            active = shipment.eta < stamp and shipment.status in ('planned','in_transit','delayed')
            row = checks.get(shipment.id)
            if not active and not row:
                continue
            digest = hashlib.sha256(json.dumps([shipment.eta.isoformat(),shipment.status,shipment.to_location_id]).encode()).hexdigest()
            if not row:
                row = MonitorRow(id='monitor_'+hashlib.sha256(shipment.id.encode()).hexdigest()[:20], shipment_id=shipment.id,
                                 location_id=shipment.to_location_id, fingerprint=digest, title='', checked_at=stamp)
                session.add(row)
            elif row.fingerprint != digest or row.status == 'resolved' and active:
                row.fingerprint, row.status = digest, 'open'
                row.revision += 1
            elif row.status == 'snoozed' and row.snoozed_until <= stamp:
                row.status = 'open';row.revision += 1
            if not active and row.status != 'resolved':
                row.status = 'resolved';row.revision += 1
            row.location_id = shipment.to_location_id
            row.title = f'{shipment.description}: recorded ETA {shipment.eta.isoformat()}Z has passed. Verify the delivery record.'
            row.checked_at = stamp
        for sid, row in checks.items():
            if not any(s.id == sid for s in shipments) and row.status != 'resolved':
                row.status = 'resolved';row.checked_at = stamp;row.revision += 1
        await session.commit()


@router.get('/monitor/findings')
async def findings(session=Depends(session_dep), actor=Depends(request_actor)):
    await scope_ok(session, actor, 'S4')
    result=[]
    for row in (await session.scalars(select(MonitorRow).order_by(MonitorRow.checked_at.desc()))).all():
        try:
            await access(session,actor,row.location_id)
            shipment = await session.get(ShipmentRow, row.shipment_id)
            if shipment and shipment.to_location_id:
                await access(session, actor, shipment.to_location_id)
        except HTTPException:
            continue
        result.append({k:getattr(row,k) for k in ('id','shipment_id','location_id','title','status','revision','checked_at','snoozed_until')} | {'history':json.loads(row.history_json)})
    return {'rule':'Recorded shipment ETA passed while delivery remains pending. This checks records, not physical arrival.', 'items':result}


@router.patch('/monitor/findings/{mid}')
async def decide(mid:str, body:MonitorDecision, session=Depends(session_dep), actor=Depends(request_actor)):
    row=await session.get(MonitorRow,mid)
    if not row:raise HTTPException(404,'Finding not found')
    await access(session,actor,row.location_id,True)
    shipment = await session.get(ShipmentRow, row.shipment_id)
    if shipment and shipment.to_location_id:
        await access(session, actor, shipment.to_location_id, True)
    if row.status=='resolved':raise HTTPException(409,'Finding is already resolved')
    history=json.loads(row.history_json)+[{'at':now().isoformat()+'Z','actor':actor.name,'action':body.action,'note':body.note}]
    changed=await session.execute(update(MonitorRow).where(MonitorRow.id==mid,MonitorRow.revision==body.revision).values(
        status={'dismiss':'dismissed','snooze':'snoozed','reopen':'open'}[body.action],revision=body.revision+1,
        snoozed_until=now()+timedelta(hours=24) if body.action=='snooze' else None,history_json=json.dumps(history)))
    if changed.rowcount!=1:raise HTTPException(409,'Finding changed; reload before reviewing')
    await session.commit()
    return {'saved':True}

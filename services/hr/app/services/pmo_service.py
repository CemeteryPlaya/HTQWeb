"""PMO service — CRUD + members + org-chart data."""

from datetime import date

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.employee import Employee
from app.models.position import Position
from app.models.pmo import PMO, PMODepartment, PMOMember, PMOPosition
from app.repositories.base_repo import BaseRepository

logger = structlog.get_logger()


class PMOService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BaseRepository(PMO, session)

    # ── PMO CRUD ───────────────────────────────────────────────────────

    async def list_pmos(self, *, status_filter: str | None = None) -> list[PMO]:
        filters = {"status": status_filter} if status_filter else None
        items, _ = await self.repo.list(filters=filters, limit=500, order_by="name")
        return list(items)

    async def get_pmo(self, id: int) -> PMO:
        pmo = await self.repo.get(id)
        if not pmo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PMO not found")
        return pmo

    async def create_pmo(self, data: dict) -> PMO:
        # Check unique code
        stmt = select(PMO).where(PMO.code == data["code"])
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"PMO with code '{data['code']}' already exists",
            )
        pmo = await self.repo.create(data)
        logger.info("pmo_created", pmo_id=pmo.id, code=pmo.code)
        return pmo

    async def update_pmo(self, id: int, data: dict) -> PMO:
        pmo = await self.get_pmo(id)
        updated = await self.repo.update(pmo, data)
        logger.info("pmo_updated", pmo_id=id)
        return updated

    async def delete_pmo(self, id: int) -> None:
        pmo = await self.get_pmo(id)
        await self.repo.delete(pmo)
        logger.info("pmo_deleted", pmo_id=id)

    # ── Members ────────────────────────────────────────────────────────

    async def list_members(self, pmo_id: int) -> list[dict]:
        await self.get_pmo(pmo_id)
        stmt = (
            select(PMOMember, Employee, Position)
            .join(Employee, PMOMember.employee_id == Employee.id)
            .outerjoin(Position, Employee.position_id == Position.id)
            .where(PMOMember.pmo_id == pmo_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": m.id,
                "pmo_id": m.pmo_id,
                "employee_id": m.employee_id,
                "employee_name": f"{e.first_name} {e.last_name}",
                "employee_email": e.email,
                "primary_position": p.title if p else None,
                "position_in_pmo": m.position_in_pmo,
                "membership_type": m.membership_type,
                "from_date": m.from_date.isoformat() if m.from_date else None,
                "to_date": m.to_date.isoformat() if m.to_date else None,
            }
            for m, e, p in rows
        ]

    async def add_member(self, pmo_id: int, data: dict) -> PMOMember:
        await self.get_pmo(pmo_id)
        # Verify employee exists
        emp = await self.session.get(Employee, data["employee_id"])
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        # Prevent duplicate
        stmt = select(PMOMember).where(
            PMOMember.pmo_id == pmo_id,
            PMOMember.employee_id == data["employee_id"],
        )
        if (await self.session.execute(stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee is already a member of this PMO",
            )
        member = PMOMember(
            pmo_id=pmo_id,
            employee_id=data["employee_id"],
            membership_type=data.get("membership_type", "permanent"),
            position_in_pmo=data.get("position_in_pmo"),
            from_date=data.get("from_date") or date.today(),
            to_date=data.get("to_date"),
        )
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        logger.info("pmo_member_added", pmo_id=pmo_id, employee_id=data["employee_id"])
        return member

    async def remove_member(self, pmo_id: int, member_id: int) -> None:
        stmt = select(PMOMember).where(PMOMember.id == member_id, PMOMember.pmo_id == pmo_id)
        member = (await self.session.execute(stmt)).scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found in this PMO")
        await self.session.delete(member)
        await self.session.flush()

    # ── PMO org-chart (for Фича 3 integration) ────────────────────────

    async def get_pmo_org_chart(self, pmo_id: int) -> dict:
        pmo = await self.get_pmo(pmo_id)
        members = await self.list_members(pmo_id)

        nodes = [
            {
                "id": f"pmo_{pmo.id}",
                "label": pmo.name,
                "type": "pmo",
                "unit_type": "pmo",
                "level": None,
                "weight": None,
                "meta": {"code": pmo.code, "status": pmo.status},
            }
        ]
        edges = []

        for m in members:
            nodes.append({
                "id": f"emp_{m['employee_id']}",
                "label": m["employee_name"],
                "type": "employee",
                "unit_type": None,
                "level": None,
                "weight": None,
                "meta": {
                    "membership_type": m["membership_type"],
                    "position_title": m["position_in_pmo"] or m["primary_position"],
                },
            })
            edges.append({
                "source": f"pmo_{pmo.id}",
                "target": f"emp_{m['employee_id']}",
                "relation_type": m["membership_type"],
            })

        return {"nodes": nodes, "edges": edges}

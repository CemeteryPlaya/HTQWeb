"""OrgService — subordination matrix, org tree, reporting relations CRUD."""

from datetime import date
from typing import Literal

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.employee import Employee
from app.models.org_settings import OrgSettings
from app.models.position import Position
from app.models.reporting_relation import ReportingRelation
from app.repositories.base_repo import BaseRepository

logger = structlog.get_logger()

RelationType = Literal["direct", "functional", "project"]
DeletionStrategy = Literal["block", "reassign_to_parent", "cascade"]


class OrgService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.dept_repo = BaseRepository(Department, session)
        self.pos_repo = BaseRepository(Position, session)
        self.rel_repo = BaseRepository(ReportingRelation, session)

    # ── Org settings ──────────────────────────────────────────────────

    async def get_deletion_strategy(self) -> DeletionStrategy:
        stmt = select(OrgSettings).where(OrgSettings.key == "deletion_strategy")
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        val = setting.value if setting else "block"
        if val not in ("block", "reassign_to_parent", "cascade"):
            return "block"
        return val  # type: ignore[return-value]

    async def set_deletion_strategy(self, strategy: DeletionStrategy) -> None:
        stmt = select(OrgSettings).where(OrgSettings.key == "deletion_strategy")
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = strategy
            self.session.add(setting)
        else:
            self.session.add(OrgSettings(key="deletion_strategy", value=strategy))
        await self.session.flush()

    # ── Department deletion with configurable strategy ─────────────────

    async def delete_department(self, id: int) -> None:
        dept = await self.dept_repo.get(id)
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

        children = await self._get_children(dept.path)
        if children:
            strategy = await self.get_deletion_strategy()
            if strategy == "block":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot delete '{dept.name}': has {len(children)} sub-unit(s). "
                           "Change deletion_strategy in org settings to allow cascade or reassign.",
                )
            elif strategy == "reassign_to_parent":
                parent_path = ".".join(dept.path.split(".")[:-1])
                parent = await self._get_dept_by_path(parent_path)
                parent_id = parent.id if parent else None
                for child in children:
                    # Re-root child one level up in the ltree
                    new_path = parent_path + "." + child.path.split(".")[-1] if parent_path else child.path.split(".")[-1]
                    child.path = new_path
                    if parent_id:
                        child.description = child.description  # touch to mark dirty
                    self.session.add(child)
            # cascade: FK ondelete is not set on departments, so delete children recursively
            elif strategy == "cascade":
                for child in children:
                    await self.session.delete(child)

        await self.session.delete(dept)
        await self.session.flush()
        logger.info("department_deleted", department_id=id, strategy=await self.get_deletion_strategy())

    async def _get_children(self, path: str) -> list[Department]:
        # Direct children only: path starts with parent_path + "." and has no further dots
        prefix = path + "."
        stmt = select(Department).where(Department.path.like(prefix + "%"))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_dept_by_path(self, path: str) -> Department | None:
        stmt = select(Department).where(Department.path == path)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Reporting relations ────────────────────────────────────────────

    async def add_relation(
        self,
        superior_id: int,
        subordinate_id: int,
        relation_type: RelationType,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> ReportingRelation:
        if superior_id == subordinate_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A position cannot be subordinate to itself",
            )
        # Check duplicate
        stmt = select(ReportingRelation).where(
            ReportingRelation.superior_position_id == superior_id,
            ReportingRelation.subordinate_position_id == subordinate_id,
            ReportingRelation.relation_type == relation_type,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This reporting relation already exists",
            )
        rel = await self.rel_repo.create({
            "superior_position_id": superior_id,
            "subordinate_position_id": subordinate_id,
            "relation_type": relation_type,
            "effective_from": effective_from or date.today(),
            "effective_to": effective_to,
        })
        logger.info("reporting_relation_added", superior=superior_id, subordinate=subordinate_id)
        return rel

    async def remove_relation(self, relation_id: int) -> None:
        rel = await self.rel_repo.get(relation_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation not found")
        await self.rel_repo.delete(rel)

    async def get_relations_for_unit(self, unit_id: int) -> list[ReportingRelation]:
        """All relations where any position belongs to the given department."""
        stmt = (
            select(ReportingRelation)
            .join(Position, ReportingRelation.superior_position_id == Position.id)
            .where(Position.department_id == unit_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Subordination matrix ───────────────────────────────────────────

    async def get_subordination_matrix(self, unit_id: int | None = None) -> dict:
        """
        Returns matrix data: list of superior positions (rows),
        list of subordinate positions (cols), and relation cells.
        """
        stmt = select(ReportingRelation)
        if unit_id is not None:
            # Filter to relations where superior belongs to this unit
            stmt = (
                stmt
                .join(Position, ReportingRelation.superior_position_id == Position.id)
                .where(Position.department_id == unit_id)
            )
        result = await self.session.execute(stmt)
        relations = list(result.scalars().all())

        superior_ids = list({r.superior_position_id for r in relations})
        subordinate_ids = list({r.subordinate_position_id for r in relations})
        all_ids = list(set(superior_ids + subordinate_ids))

        if not all_ids:
            return {"superiors": [], "subordinates": [], "cells": []}

        pos_stmt = select(Position).where(Position.id.in_(all_ids))
        pos_result = await self.session.execute(pos_stmt)
        pos_map = {p.id: p for p in pos_result.scalars().all()}

        def pos_summary(p: Position) -> dict:
            return {"id": p.id, "title": p.title, "weight": p.weight, "level": p.level}

        cells = [
            {
                "superior_position_id": r.superior_position_id,
                "subordinate_position_id": r.subordinate_position_id,
                "relation_type": r.relation_type,
                "effective_from": r.effective_from.isoformat() if r.effective_from else None,
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
            }
            for r in relations
        ]

        return {
            "superiors": [pos_summary(pos_map[i]) for i in superior_ids if i in pos_map],
            "subordinates": [pos_summary(pos_map[i]) for i in subordinate_ids if i in pos_map],
            "cells": cells,
        }

    # ── Org tree (for Фича 3) ─────────────────────────────────────────

    async def get_org_tree(
        self,
        root_id: int | None,
        depth: int,
        mode: Literal["positions", "employees", "both"],
    ) -> dict:
        """Build node/edge graph for React Flow rendering."""
        # Fetch all active departments
        dept_stmt = select(Department).where(Department.is_active == True)  # noqa: E712
        if root_id is not None:
            root = await self.dept_repo.get(root_id)
            if not root:
                raise HTTPException(status_code=404, detail="Root unit not found")
            dept_stmt = dept_stmt.where(Department.path.like(root.path + "%"))

        dept_result = await self.session.execute(dept_stmt)
        departments = list(dept_result.scalars().all())

        # Filter by depth relative to root
        root_depth = len(root.path.split(".")) if root_id else 0
        if root_id:
            departments = [
                d for d in departments
                if len(d.path.split(".")) - root_depth <= depth
            ]

        nodes: list[dict] = []
        edges: list[dict] = []

        # Department nodes
        for dept in departments:
            nodes.append({
                "id": f"dept_{dept.id}",
                "label": dept.name,
                "type": "department",
                "unit_type": dept.unit_type,
                "level": len(dept.path.split(".")),
                "weight": None,
                "meta": {"path": dept.path},
            })
            # Edge to parent department
            parts = dept.path.split(".")
            if len(parts) > 1:
                parent_path = ".".join(parts[:-1])
                parent = next((d for d in departments if d.path == parent_path), None)
                if parent:
                    edges.append({
                        "source": f"dept_{parent.id}",
                        "target": f"dept_{dept.id}",
                        "relation_type": "structural",
                    })

        if mode in ("positions", "both"):
            dept_ids = [d.id for d in departments]
            pos_stmt = select(Position).where(
                Position.department_id.in_(dept_ids),
                Position.is_active == True,  # noqa: E712
            )
            pos_result = await self.session.execute(pos_stmt)
            positions = list(pos_result.scalars().all())

            for pos in positions:
                nodes.append({
                    "id": f"pos_{pos.id}",
                    "label": pos.title,
                    "type": "position",
                    "unit_type": None,
                    "level": pos.level,
                    "weight": pos.weight,
                    "meta": {"grade": pos.grade, "department_id": pos.department_id},
                })
                edges.append({
                    "source": f"dept_{pos.department_id}",
                    "target": f"pos_{pos.id}",
                    "relation_type": "membership",
                })

            # Reporting relations between positions
            if dept_ids:
                rel_stmt = (
                    select(ReportingRelation)
                    .join(Position, ReportingRelation.superior_position_id == Position.id)
                    .where(Position.department_id.in_(dept_ids))
                )
                rel_result = await self.session.execute(rel_stmt)
                for rel in rel_result.scalars().all():
                    edges.append({
                        "source": f"pos_{rel.superior_position_id}",
                        "target": f"pos_{rel.subordinate_position_id}",
                        "relation_type": rel.relation_type,
                    })

        if mode in ("employees", "both"):
            dept_ids = [d.id for d in departments]
            emp_stmt = select(Employee).where(
                Employee.department_id.in_(dept_ids),
                Employee.status == "active",
                Employee.is_deleted == False,  # noqa: E712
            )
            emp_result = await self.session.execute(emp_stmt)
            employees = list(emp_result.scalars().all())

            for emp in employees:
                nodes.append({
                    "id": f"emp_{emp.id}",
                    "label": f"{emp.first_name} {emp.last_name}",
                    "type": "employee",
                    "unit_type": None,
                    "level": None,
                    "weight": None,
                    "meta": {
                        "avatar_url": emp.avatar_url,
                        "department_id": emp.department_id,
                        "position_id": emp.position_id,
                    },
                })
                parent = f"pos_{emp.position_id}" if mode == "both" and emp.position_id else f"dept_{emp.department_id}"
                edges.append({
                    "source": parent,
                    "target": f"emp_{emp.id}",
                    "relation_type": "employment",
                })

        return {"nodes": nodes, "edges": edges}

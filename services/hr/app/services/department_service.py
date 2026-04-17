"""Department service — business logic for department management."""

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.repositories.department_repo import DepartmentRepository
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentTree

logger = structlog.get_logger()


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DepartmentRepository(session)

    async def list_departments(self) -> list[Department]:
        return await self.repo.get_all_active()

    async def get_department(self, id: int) -> Department:
        dept = await self.repo.get(id)
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        return dept

    async def get_tree(self) -> list[DepartmentTree]:
        """Build a nested department tree from flat list."""
        all_depts = await self.repo.get_all_active()
        return _build_tree(all_depts)

    async def get_children(self, id: int) -> list[Department]:
        dept = await self.get_department(id)
        return await self.repo.get_children(dept.path)

    async def get_employees(self, id: int) -> list:
        dept = await self.repo.get_employees(id)
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        return dept.employees

    async def create_department(self, data: DepartmentCreate) -> Department:
        existing = await self.repo.get_by_path(data.path)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department path already exists")
        dept = await self.repo.create(data.model_dump())
        logger.info("department_created", department_id=dept.id, path=dept.path)
        return dept

    async def update_department(self, id: int, data: DepartmentUpdate) -> Department:
        dept = await self.get_department(id)
        patch = data.model_dump(exclude_none=True)
        updated = await self.repo.update(dept, patch)
        logger.info("department_updated", department_id=id)
        return updated

    async def delete_department(self, id: int) -> None:
        dept = await self.get_department(id)
        children = await self.repo.get_children(dept.path)
        if children:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete department with sub-departments",
            )
        await self.repo.delete(dept)
        logger.info("department_deleted", department_id=id)


def _build_tree(departments: list[Department]) -> list[DepartmentTree]:
    """Convert flat list of departments to nested tree using ltree paths."""
    from app.schemas.department import DepartmentTree as Tree

    tree_map: dict[int, Tree] = {}
    roots: list[Tree] = []

    # Build nodes
    for dept in departments:
        node = Tree.model_validate(dept)
        tree_map[dept.id] = node

    # Wire children via path prefix
    for dept in departments:
        node = tree_map[dept.id]
        parent_path = ".".join(dept.path.split(".")[:-1])
        parent = next((d for d in departments if d.path == parent_path), None)
        if parent and parent.id in tree_map:
            tree_map[parent.id].children.append(node)
        else:
            roots.append(node)

    return roots

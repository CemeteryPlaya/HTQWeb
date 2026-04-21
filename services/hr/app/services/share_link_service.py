"""ShareLinkService — generate, validate, and consume shareable org links."""

import secrets
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shareable_link import ShareableLink
from app.services.org_service import OrgService

logger = structlog.get_logger()


def _generate_token() -> str:
    """Cryptographically secure 64-char hex token."""
    return secrets.token_hex(32)


class ShareLinkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Authenticated operations ───────────────────────────────────────

    async def create_link(self, user_id: int, data: dict) -> ShareableLink:
        link = ShareableLink(
            token=_generate_token(),
            created_by_user_id=user_id,
            label=data.get("label"),
            max_level=data.get("max_level", 3),
            visible_units=data.get("visible_units"),
            link_type=data.get("link_type", "one_time"),
            expires_at=data.get("expires_at"),
            is_active=True,
        )
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)
        logger.info("share_link_created", token_prefix=link.token[:8], user_id=user_id)
        return link

    async def list_links(self, user_id: int) -> list[ShareableLink]:
        stmt = (
            select(ShareableLink)
            .where(ShareableLink.created_by_user_id == user_id)
            .order_by(ShareableLink.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_link(self, link_id: uuid.UUID, user_id: int) -> None:
        stmt = select(ShareableLink).where(
            ShareableLink.id == link_id,
            ShareableLink.created_by_user_id == user_id,
        )
        link = (await self.session.execute(stmt)).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        link.is_active = False
        self.session.add(link)
        await self.session.flush()
        logger.info("share_link_revoked", link_id=str(link_id))

    # ── Public endpoint — atomic consume ──────────────────────────────

    async def consume_link(self, token: str, request: Request) -> dict:
        """
        Validate token and return org tree.
        For one_time links: atomically set opened_at + is_active=False.
        Uses SELECT FOR UPDATE to prevent race conditions on double-open.
        """
        stmt = (
            select(ShareableLink)
            .where(ShareableLink.token == token)
            .with_for_update()
        )
        link = (await self.session.execute(stmt)).scalar_one_or_none()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        if not link.is_active:
            raise HTTPException(status_code=410, detail="This link has already been used or revoked")

        now = datetime.now(timezone.utc)
        if link.expires_at and link.expires_at < now:
            link.is_active = False
            self.session.add(link)
            await self.session.flush()
            raise HTTPException(status_code=410, detail="This link has expired")

        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.client.host  # type: ignore[union-attr]
        )

        # Mark as opened
        link.opened_at = now
        link.opened_by_ip = client_ip[:45]

        if link.link_type == "one_time":
            link.is_active = False

        self.session.add(link)
        await self.session.flush()

        # Build org tree restricted to max_level
        org_svc = OrgService(self.session)
        tree = await org_svc.get_org_tree(
            root_id=None,
            depth=link.max_level,
            mode="positions",
        )

        # Filter by visible_units if set
        if link.visible_units:
            allowed = set(str(u) for u in link.visible_units)
            tree["nodes"] = [
                n for n in tree["nodes"]
                if n["type"] != "department" or str(n.get("meta", {}).get("id", "")) in allowed
            ]

        # Strip sensitive data before returning
        for node in tree["nodes"]:
            meta = node.get("meta") or {}
            meta.pop("email", None)
            meta.pop("phone", None)
            meta.pop("salary", None)
            node["meta"] = meta

        logger.info("share_link_consumed", token_prefix=token[:8], ip=client_ip)
        return {
            "label": link.label,
            "max_level": link.max_level,
            "generated_at": link.created_at.isoformat() if link.created_at else None,
            "tree": tree,
        }

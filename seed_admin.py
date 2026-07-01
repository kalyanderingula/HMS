"""Seed default super admin user"""
import asyncio
import bcrypt
from app.config import async_session
from app.api.auth import User, Role, UserRole
from sqlalchemy import select


async def seed_admin():
    async with async_session() as db:
        # Delete old if exists
        result = await db.execute(select(User).where(User.username == "ADMIN-SUPER-00001"))
        old = result.scalars().first()
        if old:
            await db.execute(select(UserRole).where(UserRole.user_id == old.user_id))
            await db.delete(old)
            await db.commit()

        # Create with proper hash
        password = "Admin_@_01011990"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        user = User(
            username="ADMIN-SUPER-00001",
            email="admin@hospital.com",
            password_hash=password_hash,
            status="active",
        )
        db.add(user)
        await db.flush()

        result = await db.execute(select(Role).where(Role.role_name == "super_admin"))
        role = result.scalars().first()
        if role:
            db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

        await db.commit()
        print(f"Admin created successfully!")
        print(f"  Employee ID: ADMIN-SUPER-00001")
        print(f"  Password:    Admin_@_01011990")


asyncio.run(seed_admin())

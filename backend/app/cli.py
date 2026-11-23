"""Management commands.

    python -m app.cli create-admin --email admin@example.com --name "Admin Name"
    python -m app.cli seed-demo        # demonstration inventory (empty inventory only)

The password is prompted for (hidden), or read from YANA_ADMIN_PASSWORD for automation.
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError

from app.core.errors import DomainError
from app.database.session import SessionLocal
from app.models.enums import RoleCode
from app.schemas.user import UserCreate
from app.services.user_service import UserService


def _read_password() -> str:
    env_password = os.environ.get("YANA_ADMIN_PASSWORD")
    if env_password:
        return env_password
    first = getpass.getpass("Password (min 8 characters): ")
    if first != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    return first


def create_admin(email: str, name: str) -> None:
    try:
        data = UserCreate(email=email, full_name=name, role=RoleCode.ADMIN, password=_read_password())
    except ValidationError as exc:
        sys.exit("; ".join(e["msg"] for e in exc.errors()))
    with SessionLocal() as db:
        try:
            user = UserService(db).create(data)
        except DomainError as exc:
            sys.exit(exc.message)
        print(f"Administrator created: {user.email}")


def seed_demo() -> None:
    from app.seed.demo_inventory import inventory_is_empty, load_demo_inventory

    with SessionLocal() as db:
        if not inventory_is_empty(db):
            sys.exit("Inventory already contains countries; demo data was NOT loaded (it never overwrites real data).")
        counts = load_demo_inventory(db)
    print("Demo inventory loaded: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    print("Hotels, restaurants, suppliers and vehicles are fictional and marked DEMO.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create an administrator account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    sub.add_parser("seed-demo", help="Load demonstration inventory into an empty database")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.name)
    elif args.command == "seed-demo":
        seed_demo()


if __name__ == "__main__":
    main()

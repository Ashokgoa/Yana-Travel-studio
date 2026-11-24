"""Management commands.

    python -m app.cli create-admin --email admin@example.com --name "Admin Name"
    python -m app.cli seed-demo        # demonstration inventory (empty inventory only)
    python -m app.cli backup           # zip of database, uploads and PDFs into database/backups
    python -m app.cli restore FILE.zip # replace everything with a backup (stop the app first)

The password is prompted for (hidden), or read from YANA_ADMIN_PASSWORD for automation.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

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


def backup() -> None:
    from app.services.backup_service import BackupService

    try:
        info = BackupService().create(created_by="command line")
    except DomainError as exc:
        sys.exit(exc.message)
    print(f"Backup created: {info['name']} ({info['size_bytes'] // 1024} KB) in {BackupService().dir}")


def restore(path: str, yes: bool) -> None:
    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings
    from app.services.backup_service import BackupService

    if not yes:
        print("This REPLACES the database, uploaded images and generated PDFs with the backup.")
        print("A safety backup of the current state is made first. Stop YANA Travel Studio before continuing.")
        try:
            answer = input("Type RESTORE to continue: ").strip()
        except EOFError:
            answer = ""
        if answer != "RESTORE":
            sys.exit("Cancelled: nothing was changed.")
    try:
        result = BackupService().restore(Path(path))
    except DomainError as exc:
        sys.exit(exc.message)
    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")  # a backup from an older version is brought up to date
    print(f"Restored {result['restored']} (made {result['manifest'].get('created_at', '?')}).")
    if result["safety_backup"]:
        print(f"The previous state was saved as {result['safety_backup']}.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="Create an administrator account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    sub.add_parser("seed-demo", help="Load demonstration inventory into an empty database")
    sub.add_parser("backup", help="Back up the database, uploaded images and generated PDFs")
    rest = sub.add_parser("restore", help="Restore a backup zip (stop the app first)")
    rest.add_argument("file")
    rest.add_argument("--yes", action="store_true", help="Do not ask for confirmation")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.name)
    elif args.command == "seed-demo":
        seed_demo()
    elif args.command == "backup":
        backup()
    elif args.command == "restore":
        restore(args.file, args.yes)


if __name__ == "__main__":
    main()

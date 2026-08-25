"""Create a default admin user and vendor for local development."""

import argparse

from app import create_app
from vim_database.database import db
from vim_database.models import User, Vendor

def seed(fresh: bool = False):
    app = create_app()
    with app.app_context():
        if fresh:
            db.drop_all()
            db.create_all()
            print("Database recreated with current schema.")

        vendor = Vendor.query.filter_by(VendorName="Default Vendor").first()
        if not vendor:
            vendor = Vendor(
                VendorName="Default Vendor",
                GSTNumber="",
                Email="vendor@example.com",
                Status=1,
            )
            db.session.add(vendor)
            db.session.flush()

        admin = User.query.filter_by(Email="admin@vim.local").first()
        if not admin:
            admin = User(
                Username="admin",
                PasswordHash="admin123",
                Email="admin@vim.local",
                Role="admin",
                VendorID=vendor.VendorID,
                IsActive=True,
            )
            db.session.add(admin)

        db.session.commit()
        print("Seed complete.")
        print("  Login: admin@vim.local / admin123")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed VIM admin user")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Drop and recreate all tables (use when schema changed)",
    )
    args = parser.parse_args()
    seed(fresh=args.fresh)

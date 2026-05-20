from datetime import datetime

from app.db.models import User, UserAuthIdentity
from app.db.session import SessionLocal, init_db


def main() -> None:
    init_db()

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.telegram_id.isnot(None)).all()
        created = 0

        for user in users:
            provider_user_id = str(user.telegram_id)

            exists = (
                db.query(UserAuthIdentity)
                .filter(
                    UserAuthIdentity.provider == "telegram",
                    UserAuthIdentity.provider_user_id == provider_user_id,
                )
                .first()
            )

            if exists:
                continue

            identity = UserAuthIdentity(
                user_id=user.id,
                provider="telegram",
                provider_user_id=provider_user_id,
                email=user.email,
                username=user.username,
                display_name=user.first_name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(identity)
            created += 1

        db.commit()
        print(f"Backfill complete. Created identities: {created}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

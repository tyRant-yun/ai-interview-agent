from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ConversationMessageRecord,
    ConversationRecord,
)
from app.domain.conversation import (
    Conversation,
    ConversationMessage,
    ConversationRole,
)


class SQLAlchemyConversationRepository:
    """Store conversations through SQLAlchemy."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        title: str | None,
    ) -> Conversation:
        record = ConversationRecord(
            title=title,
        )

        self._session.add(record)

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(record)

        return self._to_conversation(record)

    def get(
        self,
        conversation_id: int,
    ) -> Conversation | None:
        record = self._session.get(
            ConversationRecord,
            conversation_id,
        )

        if record is None:
            return None

        return self._to_conversation(record)

    def list_messages(
        self,
        conversation_id: int,
        *,
        after_message_id: int | None = None,
    ) -> list[ConversationMessage]:
        statement = (
            select(ConversationMessageRecord)
            .where(
                ConversationMessageRecord
                .conversation_id
                == conversation_id
            )
            .order_by(
                ConversationMessageRecord.id
            )
        )

        if after_message_id is not None:
            statement = statement.where(
                ConversationMessageRecord.id
                > after_message_id
            )

        records = self._session.scalars(
            statement
        ).all()

        return [
            self._to_message(record)
            for record in records
        ]

    def append_turn(
        self,
        conversation_id: int,
        *,
        user_content: str,
        assistant_content: str,
    ) -> tuple[
        ConversationMessage,
        ConversationMessage,
    ] | None:
        conversation = self._session.get(
            ConversationRecord,
            conversation_id,
        )

        if conversation is None:
            return None

        user_record = ConversationMessageRecord(
            conversation_id=conversation_id,
            role=ConversationRole.USER.value,
            content=user_content,
        )

        assistant_record = (
            ConversationMessageRecord(
                conversation_id=conversation_id,
                role=(
                    ConversationRole
                    .ASSISTANT.value
                ),
                content=assistant_content,
            )
        )

        self._session.add_all(
            [
                user_record,
                assistant_record,
            ]
        )

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(user_record)
        self._session.refresh(
            assistant_record
        )

        return (
            self._to_message(user_record),
            self._to_message(
                assistant_record
            ),
        )

    def update_summary(
        self,
        conversation_id: int,
        *,
        summary: str,
        summarized_through_message_id: int,
    ) -> Conversation | None:
        record = self._session.get(
            ConversationRecord,
            conversation_id,
        )

        if record is None:
            return None

        record.summary = summary
        record.summarized_through_message_id = (
            summarized_through_message_id
        )

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(record)

        return self._to_conversation(record)

    @staticmethod
    def _to_conversation(
        record: ConversationRecord,
    ) -> Conversation:
        return Conversation(
            id=record.id,
            title=record.title,
            summary=record.summary,
            summarized_through_message_id=(
                record
                .summarized_through_message_id
            ),
        )

    @staticmethod
    def _to_message(
        record: ConversationMessageRecord,
    ) -> ConversationMessage:
        return ConversationMessage(
            id=record.id,
            conversation_id=(
                record.conversation_id
            ),
            role=ConversationRole(
                record.role
            ),
            content=record.content,
        )

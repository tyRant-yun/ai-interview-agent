from app.db.models import NoteRecord
from app.db.session import SessionLocal

def test_create_and_get_note(client):
    create_response = client.post(
        "/notes",
        json={
            "title": "TCP three-way handshake",
            "category": "computer-network",
            "content": "TCP uses SYN, SYN-ACK and ACK.",
            "mastery_level": "learning",
        },
    )

    assert create_response.status_code == 201

    note_id = create_response.json()["id"]

    get_response = client.get(f"/notes/{note_id}")

    assert get_response.status_code == 200
    assert get_response.json()["title"] == (
        "TCP three-way handshake"
    )


def test_duplicate_note_returns_conflict(client):
    payload = {
        "title": "TCP three-way handshake",
        "category": "computer-network",
        "content": "TCP uses SYN, SYN-ACK and ACK.",
        "mastery_level": "learning",
    }

    first_response = client.post(
        "/notes",
        json=payload,
    )

    second_response = client.post(
        "/notes",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_missing_note_returns_not_found(client):
    response = client.get("/notes/999")

    assert response.status_code == 404


def test_empty_title_returns_validation_error(client):
    response = client.post(
        "/notes",
        json={
            "title": "   ",
            "category": "network",
            "content": "invalid",
        },
    )

    assert response.status_code == 422

def test_replace_and_delete_note(client):
    create_response = client.post(
        "/notes",
        json={
            "title": "TCP handshake",
            "category": "network",
            "content": "Initial content",
            "mastery_level": "new",
        },
    )

    note_id = create_response.json()["id"]

    update_response = client.put(
        f"/notes/{note_id}",
        json={
            "title": "TCP connection setup",
            "category": "computer-network",
            "content": (
                "TCP uses SYN, SYN-ACK and ACK."
            ),
            "mastery_level": "familiar",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == (
        "TCP connection setup"
    )
    assert update_response.json()[
        "mastery_level"
    ] == "familiar"

    delete_response = client.delete(
        f"/notes/{note_id}"
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/notes/{note_id}"
    )

    assert get_response.status_code == 404

def test_list_notes_supports_filters(client):
    client.post(
        "/notes",
        json={
            "title": "TCP handshake",
            "category": "computer-network",
            "content": "TCP connection setup.",
            "mastery_level": "learning",
        },
    )

    client.post(
        "/notes",
        json={
            "title": "MySQL B+ tree",
            "category": "mysql",
            "content": "Index structure.",
            "mastery_level": "mastered",
        },
    )

    category_response = client.get(
        "/notes",
        params={
            "category": "computer-network"
        },
    )

    assert category_response.status_code == 200
    assert len(category_response.json()) == 1
    assert category_response.json()[0][
        "title"
    ] == "TCP handshake"

    mastery_response = client.get(
        "/notes",
        params={
            "mastery_level": "mastered"
        },
    )

    assert mastery_response.status_code == 200
    assert len(mastery_response.json()) == 1
    assert mastery_response.json()[0][
        "title"
    ] == "MySQL B+ tree"

def test_created_note_is_persisted_to_database(
    client,
):
    response = client.post(
        "/notes",
        json={
            "title": "Operating system process",
            "category": "operating-system",
            "content": "A process owns resources.",
            "mastery_level": "new",
        },
    )

    assert response.status_code == 201

    note_id = response.json()["id"]

    with SessionLocal() as session:
        record = session.get(
            NoteRecord,
            note_id,
        )

        assert record is not None
        assert record.title == (
            "Operating system process"
        )
        assert record.category == (
            "operating-system"
        )

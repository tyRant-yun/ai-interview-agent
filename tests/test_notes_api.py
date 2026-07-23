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

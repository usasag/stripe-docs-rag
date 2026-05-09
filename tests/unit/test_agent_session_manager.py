from app.agent.session_manager import InMemorySessionManager


def test_session_manager_creates_and_persists_messages() -> None:
    sm = InMemorySessionManager()

    session_id = sm.ensure_session(None)
    sm.add_message(session_id, role="user", content="How do I confirm a PaymentIntent?")
    sm.add_message(session_id, role="assistant", content="Use confirm endpoint.")

    msgs = sm.get_messages(session_id)

    assert len(msgs) == 2
    assert msgs[0]["turn_index"] == 0
    assert msgs[1]["turn_index"] == 1

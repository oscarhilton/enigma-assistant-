from personal_enigma.worker import worker_status


def test_worker_status() -> None:
    assert worker_status()["status"] == "idle"

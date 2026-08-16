from personal_enigma.identity import Pseudonym


def test_pseudonym_str() -> None:
    assert str(Pseudonym(value="PERSON_A4F91C")) == "PERSON_A4F91C"

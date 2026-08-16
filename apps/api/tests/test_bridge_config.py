from personal_enigma.api.bridge import (
    BRIDGE_KEYCHAIN_ACCOUNT,
    BRIDGE_KEYCHAIN_SERVICE,
    bridge_client_config_from_settings,
    generate_bridge_token,
    plan_bridge_token_install,
)


def test_generate_bridge_token_is_unique_and_long() -> None:
    a = generate_bridge_token()
    b = generate_bridge_token()
    assert a != b
    assert len(a) >= 32


def test_plan_bridge_token_install_defaults() -> None:
    plan = plan_bridge_token_install()
    assert plan.keychain_service == BRIDGE_KEYCHAIN_SERVICE
    assert plan.keychain_account == BRIDGE_KEYCHAIN_ACCOUNT
    assert len(plan.token) >= 32


def test_bridge_client_config_from_settings() -> None:
    config = bridge_client_config_from_settings(token="abc", unix_socket="/tmp/enigma.sock")
    assert config.token == "abc"
    assert config.unix_socket == "/tmp/enigma.sock"
    assert config.base_url.startswith("http://127.0.0.1")

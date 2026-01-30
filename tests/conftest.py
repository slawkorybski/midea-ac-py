"""Pytest fixtures for testing Midea Smart AC."""
import pytest
from homeassistant.const import CONF_HOST, CONF_ID, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.midea_ac.const import CONF_DEVICE_TYPE, CONF_KEY, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="1234",
        data={
            CONF_ID: "1234",
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_TOKEN: None,
            CONF_KEY: None,
            CONF_DEVICE_TYPE: 0xAC,
        }
    )

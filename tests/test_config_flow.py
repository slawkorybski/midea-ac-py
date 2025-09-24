"""Tests for the config flow."""

import logging
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_ID, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from msmart.lan import AuthenticationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.midea_ac.const import CONF_BEEP, CONF_KEY, DOMAIN

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


async def test_config_flow_options(hass: HomeAssistant) -> None:
    """Test the config flow starts with a menu with manual and discover options."""
    # Check initial flow is a menu with two options
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["discover", "manual"]

    # Check discover flow can be started
    discover_form_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "discover"}
    )
    assert discover_form_result["type"] is FlowResultType.FORM
    assert discover_form_result["step_id"] == "discover"
    assert not discover_form_result["errors"]

    # Check manual flow can be started
    manual_form_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "manual"}
    )
    assert manual_form_result["type"] is FlowResultType.FORM
    assert manual_form_result["step_id"] == "manual"
    assert not manual_form_result["errors"]


async def test_manual_flow_invalid_input(hass: HomeAssistant) -> None:
    """Test the manual flow validates input."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "manual"}
    )
    assert result

    invalid_input = [
        {
            CONF_HOST: None
        },
        {
            CONF_HOST: "localhost",
            CONF_PORT: None
        },
        {
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_ID: None
        }
    ]
    for input in invalid_input:
        with pytest.raises(InvalidData):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input=input
            )

    # Check that invalid token/keys formats throw an error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_ID: "1234",
            CONF_TOKEN: "not_hex_string",
            CONF_KEY: "also_not_hex"

        }
    )
    assert result

    # Inputs should be marked as invalid
    assert result["errors"] == {
        CONF_TOKEN: "invalid_hex_format",
        CONF_KEY: "invalid_hex_format"
    }


async def test_manual_flow_cant_connect_v2(hass: HomeAssistant) -> None:
    """Test the manual flow returns error when connection fails on V2 devices."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "manual"}
    )
    assert result

    # Check manually configuring a V2 device
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.authenticate = AsyncMock()
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=False)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
                CONF_ID: "1234",

            }
        )
        assert result

        # Refresh should be called
        device.refresh.assert_awaited_once()

        # Authenticate should be called
        device.authenticate.assert_not_awaited()

        # Connection should fail
        assert result["errors"] == {"base": "cannot_connect"}


async def test_manual_flow_cant_connect_v3(hass: HomeAssistant) -> None:
    """Test the manual flow returns error when authenticate succeeds but refresh fails."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "manual"}
    )
    assert result

    # Check manually configuring a V3 device that can't connect
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.authenticate = AsyncMock()
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=False)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
                CONF_ID: "1234",
                CONF_TOKEN: "1234",
                CONF_KEY: "1234"

            }
        )
        assert result

        # Authenticate should be called
        device.authenticate.assert_awaited_once()

        # Refresh should be not called
        device.refresh.assert_awaited_once()

        # Connection should fail
        assert result["errors"] == {"base": "cannot_connect"}


async def test_manual_flow_cant_authenticate(hass: HomeAssistant) -> None:
    """Test the manual flow returns error when authentication fails."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "manual"}
    )
    assert result

    # Check manually configuring a V3 device that can't authenticate
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.authenticate = AsyncMock(side_effect=AuthenticationError)
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=False)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
                CONF_ID: "1234",
                CONF_TOKEN: "1234",
                CONF_KEY: "1234"

            }
        )
        assert result

        # Authenticate should be called
        device.authenticate.assert_awaited_once()

        # Refresh should be not called
        device.refresh.assert_not_awaited()

        # Connection should fail
        assert result["errors"] == {"base": "cannot_connect"}


async def test_manual_flow_unsupported_device(hass: HomeAssistant) -> None:
    """Test the manual flow when an unsupported device is configured."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "manual"}
    )
    assert result

    # Test configuring a device that is unsupported
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=True)
        type(device).supported = PropertyMock(return_value=False)

        # Manually configure a device
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
                CONF_ID: "1234"
            }
        )
        assert result

        # Refresh should be called
        device.refresh.assert_awaited_once()

        # Connection should fail
        assert result["errors"] == {"base": "unsupported_device"}


async def test_options_flow_init(hass: HomeAssistant) -> None:
    """Test the integration options flow works and default options are set."""

    # Create a mock config entry
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ID: "1234",
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_TOKEN: None,
            CONF_KEY: None,
        }
    )

    # Patch refresh and get_capabilities calls to allow integration to setup
    with (patch("custom_components.midea_ac.config_flow.AC.get_capabilities"),
          patch("custom_components.midea_ac.config_flow.AC.refresh")):
        # Add mock config entry to HASS and setup integration
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert mock_config_entry.state is ConfigEntryState.LOADED

    # Show options form
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["step_id"] == "init"
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with patch("custom_components.midea_ac.async_setup_entry",
               return_value=True) as mock_setup_entry:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_BEEP: False
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {
        CONF_BEEP: False,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reconfigure_flow_invalid_input(hass: HomeAssistant) -> None:
    """Test the reconfigure flow validates input."""

    # Create a mock config entry
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ID: "1234",
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_TOKEN: None,
            CONF_KEY: None,
        }
    )

    # Patch refresh and get_capabilities calls to allow integration to setup
    with (patch("custom_components.midea_ac.config_flow.AC.get_capabilities"),
          patch("custom_components.midea_ac.config_flow.AC.refresh")):
        # Add mock config entry to HASS and setup integration
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert mock_config_entry.state is ConfigEntryState.LOADED

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        }
    )
    assert result

    invalid_input = [
        {
            CONF_HOST: None
        },
        {
            CONF_HOST: "localhost",
            CONF_PORT: None
        }
    ]
    for input in invalid_input:
        with pytest.raises(InvalidData):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input=input
            )

    # Check that invalid token/keys formats throw an error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_TOKEN: "not_hex_string",
            CONF_KEY: "also_not_hex"

        }
    )
    assert result

    # Inputs should be marked as invalid
    assert result["errors"] == {
        CONF_TOKEN: "invalid_hex_format",
        CONF_KEY: "invalid_hex_format"
    }


async def test_reconfigure_flow_cant_connect(hass: HomeAssistant) -> None:
    """Test the reconfigure flow returns error when connection fails."""

    # Create a mock config entry
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ID: "1234",
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_TOKEN: None,
            CONF_KEY: None,
        }
    )

    # Patch refresh and get_capabilities calls to allow integration to setup
    with (patch("custom_components.midea_ac.config_flow.AC.get_capabilities"),
          patch("custom_components.midea_ac.config_flow.AC.refresh")):
        # Add mock config entry to HASS and setup integration
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert mock_config_entry.state is ConfigEntryState.LOADED

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        }
    )
    assert result

    # Check reconfiguring a V2 device
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.authenticate = AsyncMock()
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=False)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
            }
        )
        assert result

        # Refresh should be called
        device.refresh.assert_awaited_once()

        # Authenticate shouldn't be called
        device.authenticate.assert_not_awaited()

        # Connection should fail
        assert result["errors"] == {"base": "cannot_connect"}

    # Check reconfiguring a V3 device
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.authenticate = AsyncMock()
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=False)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
                CONF_TOKEN: "1234",
                CONF_KEY: "1234"

            }
        )
        assert result

        # Authenticate should be called
        device.authenticate.assert_awaited_once()

        # Refresh should be called
        device.refresh.assert_awaited_once()

        # Connection should fail
        assert result["errors"] == {"base": "cannot_connect"}

    # Check manually configuring a V3 device that can't authenticate
    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.authenticate = AsyncMock(side_effect=AuthenticationError)
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=False)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
                CONF_TOKEN: "1234",
                CONF_KEY: "1234"

            }
        )
        assert result

        # Authenticate should be called
        device.authenticate.assert_awaited_once()

        # Refresh should be not called
        device.refresh.assert_not_awaited()

        # Connection should fail
        assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_flow_unsupported_device(hass: HomeAssistant) -> None:
    """Test the reconfigure flow when an unsupported device is configured."""

    # Create a mock config entry
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ID: "1234",
            CONF_HOST: "localhost",
            CONF_PORT: 6444,
            CONF_TOKEN: None,
            CONF_KEY: None,
        }
    )

    # Patch refresh and get_capabilities calls to allow integration to setup
    with (patch("custom_components.midea_ac.config_flow.AC.get_capabilities"),
          patch("custom_components.midea_ac.config_flow.AC.refresh")):
        # Add mock config entry to HASS and setup integration
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert mock_config_entry.state is ConfigEntryState.LOADED

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        }
    )
    assert result

    with patch("custom_components.midea_ac.config_flow.AC", autospec=True) as mock_ac:
        device = mock_ac.return_value
        device.refresh = AsyncMock()
        type(device).online = PropertyMock(return_value=True)
        type(device).supported = PropertyMock(return_value=False)

        # Manually configure a device
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 6444,
            }
        )
        assert result

        # Refresh should be called
        device.refresh.assert_awaited_once()

        # Connection should fail
        assert result["errors"] == {"base": "unsupported_device"}

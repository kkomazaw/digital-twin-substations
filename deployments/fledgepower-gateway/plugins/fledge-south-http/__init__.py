"""
Fledge South Plugin: HTTP Polling
Poll IED simulators via HTTP/REST for telemetry data
"""
from fledge.plugins.south.common.common import *
import requests
import asyncio
import logging
from datetime import datetime

__author__ = "Digital Twin Substations"
__copyright__ = "Copyright (c) 2026"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logging.getLogger(__name__)

_CONFIG_CATEGORY_NAME = "HTTP_POLL"
_CONFIG_CATEGORY_DESCRIPTION = "HTTP Polling South Plugin"

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'HTTP Polling South Plugin',
        'type': 'string',
        'default': 'http_poll',
        'readonly': 'true'
    },
    'asset_name': {
        'description': 'Asset name',
        'type': 'string',
        'default': 'substation_telemetry',
        'order': '1',
        'displayName': 'Asset Name'
    },
    'url': {
        'description': 'IED HTTP endpoint URL',
        'type': 'string',
        'default': 'http://ied-simulator.ot-zone.svc.cluster.local:8080/telemetry',
        'order': '2',
        'displayName': 'IED URL'
    },
    'poll_interval': {
        'description': 'Polling interval in seconds',
        'type': 'integer',
        'default': '1',
        'order': '3',
        'displayName': 'Poll Interval (sec)'
    },
    'timeout': {
        'description': 'HTTP request timeout in seconds',
        'type': 'integer',
        'default': '5',
        'order': '4',
        'displayName': 'Timeout (sec)'
    }
}


def plugin_info():
    """Return plugin information"""
    return {
        'name': 'http_poll',
        'version': '1.0.0',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """Initialize plugin with configuration"""
    _LOGGER.info('HTTP Polling South plugin initialized')

    handle = {
        'asset_name': config['asset_name']['value'],
        'url': config['url']['value'],
        'poll_interval': int(config['poll_interval']['value']),
        'timeout': int(config['timeout']['value']),
        'session': requests.Session()
    }

    _LOGGER.info(f"Configured to poll {handle['url']} every {handle['poll_interval']}s")

    return handle


async def plugin_poll(handle):
    """
    Poll IED endpoint for data

    Args:
        handle: Plugin handle

    Returns:
        List of readings
    """
    try:
        url = handle['url']
        timeout = handle['timeout']
        asset_name = handle['asset_name']
        session = handle['session']

        response = session.get(url, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        # Transform to Fledge reading format
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

        readings = []
        reading = {
            'asset': asset_name,
            'timestamp': timestamp,
            'readings': data
        }
        readings.append(reading)

        return readings

    except requests.exceptions.RequestException as e:
        _LOGGER.error(f"HTTP request failed: {e}")
        return []
    except Exception as e:
        _LOGGER.error(f"Plugin poll error: {e}")
        return []


def plugin_shutdown(handle):
    """Shutdown plugin and cleanup"""
    try:
        if handle.get('session'):
            handle['session'].close()
            _LOGGER.info("HTTP session closed")
    except Exception as e:
        _LOGGER.error(f"Error during shutdown: {e}")


def plugin_reconfigure(handle, new_config):
    """Reconfigure plugin"""
    _LOGGER.info("Reconfiguring HTTP Polling South plugin")

    plugin_shutdown(handle)
    new_handle = plugin_init(new_config)

    _LOGGER.info("Plugin reconfigured successfully")

    return new_handle


def plugin_register_ingest(handle, callback, ingest_ref):
    """Register ingest callback"""
    handle['callback'] = callback
    handle['ingest_ref'] = ingest_ref

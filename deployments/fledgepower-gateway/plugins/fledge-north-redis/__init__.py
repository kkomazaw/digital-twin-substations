"""
Fledge North Plugin: Redis Streams
Send data from Fledge to Redis Streams for downstream processing
"""
from fledge.plugins.north.common.common import *
import redis
import json
import asyncio
import logging

__author__ = "Digital Twin Substations"
__copyright__ = "Copyright (c) 2026"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logging.getLogger(__name__)

_CONFIG_CATEGORY_NAME = "REDIS_STREAM"
_CONFIG_CATEGORY_DESCRIPTION = "Redis Stream North Plugin"

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Redis Stream North Plugin',
        'type': 'string',
        'default': 'redis_stream',
        'readonly': 'true'
    },
    'host': {
        'description': 'Redis host',
        'type': 'string',
        'default': 'redis.data-zone.svc.cluster.local',
        'order': '1',
        'displayName': 'Redis Host'
    },
    'port': {
        'description': 'Redis port',
        'type': 'integer',
        'default': '6379',
        'order': '2',
        'displayName': 'Redis Port'
    },
    'stream_name': {
        'description': 'Redis stream name',
        'type': 'string',
        'default': 'fledge-telemetry',
        'order': '3',
        'displayName': 'Stream Name'
    },
    'max_length': {
        'description': 'Maximum stream length',
        'type': 'integer',
        'default': '10000',
        'order': '4',
        'displayName': 'Max Stream Length'
    },
    'source': {
        'description': 'Data source identifier',
        'type': 'string',
        'default': 'fledgepower',
        'order': '5',
        'displayName': 'Source ID'
    }
}


def plugin_info():
    """Return plugin information"""
    return {
        'name': 'redis_stream',
        'version': '1.0.0',
        'type': 'north',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """Initialize plugin with configuration"""
    _LOGGER.info('Redis Stream North plugin initialized')

    handle = {
        'host': config['host']['value'],
        'port': int(config['port']['value']),
        'stream_name': config['stream_name']['value'],
        'max_length': int(config['max_length']['value']),
        'source': config['source']['value'],
        'redis_client': None
    }

    try:
        handle['redis_client'] = redis.Redis(
            host=handle['host'],
            port=handle['port'],
            decode_responses=False
        )
        handle['redis_client'].ping()
        _LOGGER.info(f"Connected to Redis at {handle['host']}:{handle['port']}")
    except Exception as e:
        _LOGGER.error(f"Failed to connect to Redis: {e}")
        raise

    return handle


async def plugin_send(handle, payloads, stream_id):
    """
    Send data to Redis Stream

    Args:
        handle: Plugin handle
        payloads: List of readings to send
        stream_id: Stream ID

    Returns:
        Tuple of (sent_count, failed_count, last_object_id)
    """
    try:
        redis_client = handle['redis_client']
        stream_name = handle['stream_name']
        max_length = handle['max_length']
        source = handle['source']

        sent_count = 0

        for payload in payloads:
            try:
                # Transform Fledge reading to our format
                data = {
                    'source': source,
                    'timestamp': payload.get('timestamp', ''),
                    'asset_code': payload.get('asset_code', ''),
                    'readings': payload.get('readings', {}),
                    'user_timestamp': payload.get('user_ts', '')
                }

                # Add to Redis Stream
                message_id = redis_client.xadd(
                    stream_name,
                    {'data': json.dumps(data)},
                    maxlen=max_length
                )

                sent_count += 1

                if sent_count % 100 == 0:
                    _LOGGER.debug(f"Sent {sent_count} messages to {stream_name}")

            except Exception as e:
                _LOGGER.error(f"Failed to send payload: {e}")
                continue

        _LOGGER.info(f"Sent {sent_count}/{len(payloads)} messages to Redis stream '{stream_name}'")

        return sent_count, len(payloads) - sent_count, stream_id

    except Exception as e:
        _LOGGER.error(f"Plugin send error: {e}")
        return 0, len(payloads), stream_id


def plugin_shutdown(handle):
    """Shutdown plugin and cleanup"""
    try:
        if handle.get('redis_client'):
            handle['redis_client'].close()
            _LOGGER.info("Redis connection closed")
    except Exception as e:
        _LOGGER.error(f"Error during shutdown: {e}")


def plugin_reconfigure(handle, new_config):
    """Reconfigure plugin"""
    _LOGGER.info("Reconfiguring Redis Stream North plugin")

    plugin_shutdown(handle)
    new_handle = plugin_init(new_config)

    _LOGGER.info("Plugin reconfigured successfully")

    return new_handle

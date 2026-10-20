"""Allowlisted, bounded local demo handlers. Never import or evaluate payload code."""


class HandlerFailure(ValueError):
    pass


def noop(payload):
    return None


def uppercase(payload):
    text = payload.get('text')
    if not isinstance(text, str) or len(text) > 10000:
        raise HandlerFailure('invalid_text')
    return {'text': text.upper()}


HANDLERS = {'noop': noop, 'uppercase': uppercase}


def execute(payload):
    if isinstance(payload, dict) and payload.get('demo_fail') is True:
        raise HandlerFailure('demo_failure')
    name = payload.get('handler', 'noop') if isinstance(payload, dict) else 'noop'
    if not isinstance(name, str) or name not in HANDLERS:
        raise HandlerFailure('unknown_handler')
    return HANDLERS[name](payload)

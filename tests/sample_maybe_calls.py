"""
Sample file to test maybeCalls detection.

This file contains duck-typed code where static type resolution should fail,
triggering maybeCalls relationships to be created.
"""


# Target classes with methods that could be called via duck typing
class FileHandler:
    def process(self, data):
        """Process file data."""
        return f"FileHandler processed: {data}"

    def save(self, path):
        """Save to file."""
        pass


class NetworkHandler:
    def process(self, data):
        """Process network data."""
        return f"NetworkHandler processed: {data}"

    def save(self, path):
        """Save to network location."""
        pass


class DatabaseHandler:
    def process(self, data):
        """Process database records."""
        return f"DatabaseHandler processed: {data}"

    def save(self, path):
        """Save to database."""
        pass


# Duck-typed functions - these should create maybeCalls
def process_with_handler(handler, data):
    """Handler type is unknown - duck typing.

    Should create maybeCalls to:
    - FileHandler.process
    - NetworkHandler.process
    - DatabaseHandler.process
    """
    result = handler.process(data)
    handler.save("/tmp/output")
    return result


def batch_process(handlers, items):
    """Process multiple items with multiple handlers.

    Should create maybeCalls for process() method.
    """
    results = []
    for handler in handlers:
        for item in items:
            results.append(handler.process(item))
    return results


class Processor:
    """A class that uses duck-typed handlers."""

    def __init__(self, handler):
        # handler type unknown at static analysis time
        self.handler = handler

    def run(self, data):
        """Should create maybeCalls since self.handler type is unknown."""
        return self.handler.process(data)

    def execute_callback(self, callback, value):
        """Callback is duck-typed - should create maybeCalls for __call__."""
        return callback(value)


# Interface-like pattern without ABC
class Logger:
    def log(self, message):
        print(message)


class FileLogger:
    def log(self, message):
        with open("log.txt", "a") as f:
            f.write(message + "\n")


class ConsoleLogger:
    def log(self, message):
        print(f"[CONSOLE] {message}")


def log_message(logger, msg):
    """Logger type unknown - should create maybeCalls to all log() methods."""
    logger.log(msg)


# Strategy pattern with duck typing
def apply_strategy(strategy, data):
    """Strategy type unknown - should create maybeCalls to execute()."""
    return strategy.execute(data)


class UpperStrategy:
    def execute(self, data):
        return data.upper()


class LowerStrategy:
    def execute(self, data):
        return data.lower()


class ReverseStrategy:
    def execute(self, data):
        return data[::-1]

ACTIVATE_DEBUG = True
def set_debug_mode(mode: bool):
    global ACTIVATE_DEBUG
    ACTIVATE_DEBUG = mode
def print_debug(*args, sep=' ', end='\n'):
    if not ACTIVATE_DEBUG: return
    """
    Prints a debug message to the console.
    The content surrounded with [] will be yellow and bold, while the rest of the message will be white and normal.
    """
    message = sep.join(str(arg) for arg in args)
    # ANSI escape codes for colors and styles
    YELLOW_BOLD = '\033[1;33m'
    WHITE_NORMAL = '\033[0;37m'
    RESET = '\033[0m'

    # Split the message into parts based on the brackets
    parts = []
    start = 0
    while True:
        start_idx = message.find('[', start)
        if start_idx == -1:
            parts.append((WHITE_NORMAL, message[start:]))
            break
        end_idx = message.find(']', start_idx)
        if end_idx == -1:
            parts.append((WHITE_NORMAL, message[start:]))
            break
        parts.append((WHITE_NORMAL, message[start:start_idx]))
        parts.append((YELLOW_BOLD, message[start_idx + 1:end_idx]))
        start = end_idx + 1

    # Print each part with the appropriate color/style
    for color, text in parts:
        print(f"{color}{text}{RESET}", end='')
    print()  # New line at the end


if __name__ == "__main__":
    print_debug("This is a [debug] message with [highlighted] parts.")
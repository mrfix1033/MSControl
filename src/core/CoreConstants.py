import os
import sys

import colorama

program_name = "ActionMulticast"
version = "beta-13"
greeting = lambda server_or_client: f"{program_name}{server_or_client}-{version} by mrfix1033 (VK: mrfix1033, Telegram: @mrfix1033)"
platform_to_extension = {"win32": ".exe"}


def init():
    os.chdir(os.path.dirname(sys.executable))
    colorama.init()
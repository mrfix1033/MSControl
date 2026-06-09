import typing
from logging import Logger

from src.core.CoreCommands import BaseCommand
from src.core.utils import StartupUtils
from src.core.utils.CommandsUtils import *


class RestartCommand(BaseCommand):
    def __init__(self, restart_func: typing.Callable):
        self.restart_func = restart_func

    def get_usage(self) -> str:
        return "restart - перезапустить программу (потеряете 20МБ ОЗУ, также можно перезагрузить пк)"

    def execute(self, args: list[str]):
        self.restart_func()


class StopCommand(BaseCommand):
    def __init__(self, stop_func: typing.Callable):
        self.stop_func = stop_func

    def get_usage(self) -> str:
        return "stop - остановить программу"

    def execute(self, args: list[str]):
        self.stop_func()


class StartupCommand(BaseCommand):
    def get_usage(self) -> str:
        return "startup add/remove - добавить/убрать программу из автозагрузки"

    def execute(self, args: list[str]):
        if len(args) < 1:
            not_enough_arguments(self.get_usage())
            return
        action = args[0]
        if action == "add":
            StartupUtils.add_to_startup("Client")
            Logger.log(f"Программа добавлена в автозагрузку")
        elif action == "remove":
            StartupUtils.remove_from_startup("Client")
            Logger.log("Программа удалена из автозагрузки")
        else:
            incorrect_usage(self.get_usage())
            return

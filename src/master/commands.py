import typing
from abc import ABC

from src.core.CoreCommands import BaseCommand
from src.core.protocol.FromServer import FindPacket
from src.core.utils import StartupUtils, StringUtils
from src.core.utils.CommandsUtils import *
from src.core.utils.StringUtils import is_correct_ip
from src.master.ServerUtils import UpdateAllClientsData


class ShutdownCommand(BaseCommand, ABC):
    def __init__(self, ip_func, server_func, all_clients_func, all_func):
        self.ip_func = ip_func
        self.server_func = server_func
        self.all_clients_func = all_clients_func
        self.all_func = all_func

    def execute(self, args: list[str]):
        if not args:
            not_enough_arguments(self.get_usage())
            return
        if args[0] == "all":
            self.all_func()
        elif args[0] == "all_clients":
            self.all_clients_func()
        elif args[0] == "master":
            self.server_func()
        else:
            if not is_correct_ip(args[0]):
                incorrect_usage(self.get_usage())
                return
            self.ip_func(args[0])


class RestartCommand(ShutdownCommand):
    def get_usage(self) -> str:
        return "restart <IP>/master/all_clients/all - перезапустить программу на: определённом компьютере/сервере(здесь)/всех клиентах/везде (потеряете 20МБ ОЗУ, также можно перезагрузить пк)"


class StopCommand(ShutdownCommand):
    def get_usage(self) -> str:
        return "stop <IP>/master/all_clients/all - остановить программу на: определённом компьютере/сервере(здесь)/всех клиентах/везде"


class ClientsConsole(BaseCommand):
    def __init__(self, func_to_hide: typing.Callable, func_to_show: typing.Callable):
        self.func_to_hide = func_to_hide
        self.func_to_show = func_to_show

    def get_usage(self) -> str:
        return "clients_console hide/show - скрыть/показать консоль у всех клиентов"

    def execute(self, args: list[str]):
        if not args:
            not_enough_arguments(self.get_usage())
            return
        if args[0] == "hide":
            self.func_to_hide()
            Logger.log("Консоль у клиентов скрыта")
        elif args[0] == "show":
            Logger.log("Консоль у клиентов открыта")
            self.func_to_show()
        else:
            incorrect_usage(self.get_usage())


class UpdateAllClients(BaseCommand):
    def __init__(self, func_to_update: typing.Callable[[str], None]):
        self.func_to_update = func_to_update

    def get_usage(self) -> str:
        return "update_all_clients <путь к файлу> - отправляет file всем клиентам, они обновляются (но не перезапускаются)"

    def execute(self, args: list[str]):
        if not args:
            not_enough_arguments(self.get_usage())
            return
        path_to_file = StringUtils.to_str_and_join(*args).strip("\"'")
        Logger.log("Начата рассылка...")
        self.func_to_update(path_to_file)
        Logger.log("Рассылка окончена")


class Count(BaseCommand):
    def __init__(self, func_to_get_count: typing.Callable[[], int]):
        self.func_to_get_count = func_to_get_count

    def get_usage(self) -> str:
        return "count - выводит количество подключенных клиентов"

    def execute(self, args: list[str]):
        Logger.log(self.func_to_get_count())


class StartupCommand(BaseCommand):
    """
    @:param func_for_client - в функцию передается флаг (добавлять в автозагрузку?), если False, то нужно убрать
    """

    def __init__(self, func_for_client: typing.Callable[[bool], None]):
        self.func_for_client = func_for_client

    def get_usage(self) -> str:
        return "startup add/remove clients/master - добавить/убрать клиентам/серверу программу из автозагрузки"

    def execute(self, args: list[str]):
        if len(args) != 2:
            not_enough_arguments(self.get_usage())
            return
        action, whom = args
        if whom == "master":
            if action == "add":
                StartupUtils.add_to_startup("Server")
                Logger.log(f"Программа добавлена в автозагрузку")
            elif action == "remove":
                StartupUtils.remove_from_startup("Server")
                Logger.log("Программа удалена из автозагрузки")
            else:
                incorrect_usage(self.get_usage())
        elif whom == "clients":
            if action == "add":
                self.func_for_client(True)
                Logger.log("Клиентам отправлена команда добавить приложение в автозагрузку")
            elif action == "remove":
                self.func_for_client(False)
                Logger.log("Клиентам отправлена команда убрать приложение из автозагрузки")
            else:
                incorrect_usage(self.get_usage())
        else:
            incorrect_usage(self.get_usage())
            return


class UpdateAllClientsInfo(BaseCommand):
    def __init__(self, data_getter: typing.Callable[[], UpdateAllClientsData]):
        self.data_getter = data_getter

    def get_usage(self) -> str:
        return "update_all_clients_info - показывает статистику по обновлению всех клиентов"

    def execute(self, args: list[str]):
        data = self.data_getter()
        if data is None:
            Logger.log("Команда обновления не вызывалась")
            return
        Logger.log(f"Обновленные ({len(data.updated_ips)}):", StringUtils.to_str_and_join(*data.updated_ips))
        Logger.log(f"Ошибка обновления ({len(data.failed_ips)}):", StringUtils.to_str_and_join(*data.failed_ips))
        unknown_ips = data.client_ips.copy()
        for ip in data.failed_ips + data.updated_ips:
            unknown_ips.remove(ip)
        Logger.log(f"Неизвестно ({len(unknown_ips)}):", StringUtils.to_str_and_join(*unknown_ips))
        Logger.log("Всего:", len(data.client_ips))


class Find(BaseCommand):
    def __init__(self, func_to_send_find: typing.Callable[[str, FindPacket.find_types_literal], bool]):
        self.func_to_send_find = func_to_send_find

    def get_usage(self) -> str:
        return "find <sound/video/all> <ip1 ip2 ip3...> - дать звуковой/видео/оба сигнал на IPs"

    def execute(self, args: list[str]):
        if len(args) < 2:
            not_enough_arguments(self.get_usage())
            return

        find_type, ips = args[0], args[1:]

        if find_type not in FindPacket.find_types:
            Logger.log(incorrect_usage(self.get_usage()))
            return

        incorrect_ips = [ip for ip in ips if not is_correct_ip(ip)]
        if incorrect_ips:
            Logger.log("Присутствуют некорректные IP, команда не выполнена:", *incorrect_ips)
            return

        bad_ips = []
        for ip in ips:
            if not self.func_to_send_find(ip, find_type):
                bad_ips.append(ip)

        if bad_ips:
            Logger.log("Эти IP не подключены:", *bad_ips)

import sys
import threading

sys.excepthook = lambda *a: traceback.print_last()
threading.excepthook = sys.excepthook

import asyncio
import socket
import time
import traceback

import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication

import src.core.utils.CommandsListener
from src.core import CoreConstants, Configuration
from src.core.CoreCommands import *
from src.core.Exceptions import LastReleaseAlreadyInstalled
from src.core.Network import serialize_packet
from src.core.protocol.FromClient import UpdateClientResultPacket
from src.core.protocol.FromServer import ClientsConsoleVisiblePacket, \
    UpdateClientPacket, StartupPacket, \
    IAmServerPacket
from src.core.protocol.Mouse import *
from src.core.protocol.Screen import ScreenPacket
from src.core.utils.PacketUtils import PacketBuilder
from src.master.commands import *
from src.slave.gui import MainWindow


class Server:
    def __init__(self):
        self.version = CoreConstants.version
        self.commands_buffer = PacketBuilder()
        self.running = True

        self.threads = []
        self.clients: dict[str, socket.socket] = {}
        self.server = None
        self.server_udp = None
        self.update_all_clients_data = None

        self.config = Configuration.YamlConfig("config_server.yml")

        self.keyboard_listener = None
        self.mouse_listener = None

        def stop_running():
            self.running = False
        self.gui = MainWindow(self.send_to_all_clients, stop_running)

    def init(self):
        if self.config.auto_enable_startup:
            StartupUtils.add_to_startup("Server")

        self.threads = [
            threading.Thread(target=self.start_handle_input),
            threading.Thread(target=lambda: asyncio.run(self.start_server())),
            threading.Thread(target=lambda: asyncio.run(self.start_server_broadcasting())),
        ]
        for thread in self.threads:
            thread.start()
        self.start_listen_actions()

    def join(self):
        for thread in self.threads:
            Logger.log("Крепление к потоку", thread)
            thread.join()
        Logger.log("Все потоки завершены")

    def update(self):
        try:
            self.updater.update()
        except LastReleaseAlreadyInstalled:
            Logger.log("Нет обновлений")

    def start_handle_input(self):
        commands_map = {
            "startup": StartupCommand(self.clients_startup),
            "update": UpdateCommand(self.update),
            "clients_console": ClientsConsole(lambda: self.send_to_all_clients(ClientsConsoleVisiblePacket(False)),
                                              lambda: self.send_to_all_clients(ClientsConsoleVisiblePacket(True))),
            "update_all_clients": UpdateAllClients(self.update_all_clients),
            "update_all_clients_info": UpdateAllClientsInfo(lambda: self.update_all_clients_data),
            "count": Count(lambda: len(self.clients)),
            "find": Find(self.find_func),
            "stop": StopCommand(None, self.stop, None, None),
            "version": Version(self.version),
        }
        commands_map["help"] = HelpCommand(list(commands_map.values()))
        src.core.utils.CommandsListener.start_listen_commands(commands_map, lambda: self.running)
        Logger.log("Обработка команд прекращена")

    def stop_logic(self):
        self.running = False
        global is_main_loop_running
        is_main_loop_running = False

        self.stop_listen_actions()

        for client in self.clients.values():
            try:
                client.close()
            except:
                pass

        if self.server is not None:
            self.server.close()
        if self.server_udp is not None:
            self.server_udp.close()

    def stop(self):
        Logger.log("Завершение работы...")
        self.stop_logic()
        Logger.log("Ожидание завершения работы...")

    async def start_server_broadcasting(self):
        while self.running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as self.server_udp:
                    self.server_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    self.server_udp.bind((self.config.ip, self.config.port))
                    Logger.log("Маячковый сервер запущен")
                    while self.running:
                        self.server_udp.sendto(serialize_packet(IAmServerPacket()),
                                               ("255.255.255.255", self.config.beacon_port))
                        await asyncio.sleep(self.config.beacon_interval)
            except Exception:
                traceback.print_exc()
            finally:
                Logger.log("Маячковый сервер остановлен")

    async def start_server(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.server:
                self.server.bind((self.config.ip, self.config.port))
                self.server.listen(1000)
                Logger.log("Основной сервер запущен")
                await self.accept_clients()
        finally:
            Logger.log("Основной сервер остановлен")

    async def accept_clients(self):
        while self.running:
            try:
                client_socket, client_ip_port = self.server.accept()
                self.clients[client_ip_port[0]] = client_socket
                client_thread = threading.Thread(target=lambda: self.listen_client(client_socket, client_ip_port))
                client_thread.start()
                self.threads.append(client_thread)
                Logger.log(f"{len(self.clients)}) Подключен {client_ip_port}")
            except InterruptedError:
                continue
            except:
                if self.running:
                    Logger.error(traceback.format_exc())

    def listen_client(self, client_socket: socket.socket, ip_port):
        packet_builder = PacketBuilder()
        while self.running:
            try:
                data = client_socket.recv(self.config.packet_size)
            except ConnectionError:
                self.clients.pop(ip_port[0])
                Logger.log(f"{len(self.clients)}) Соединение потеряно {ip_port}")
                break
            except:
                if self.running:
                    Logger.error(traceback.format_exc())
                continue
            if not data:
                return
            packet_builder.put(data)
            while True:
                bytes_excess = packet_builder.get()
                if bytes_excess is not None:
                    packet_name, buffer = packet_builder.packet_name, packet_builder.buffer
                    # если команда выдаст ошибку, она будет всё равно удалена из пакетбилдера
                    packet_builder = PacketBuilder(bytes_excess)
                    self.handle_command(ip_port, packet_name, buffer)
                else:
                    break

    def handle_command(self, ip_port, packet_name, packet_data):
        if packet_name == UpdateClientResultPacket.get_id():
            packet = UpdateClientResultPacket.deserialize(packet_data)
            self.update_all_clients_data.handle(ip_port[0], packet.is_successful)
        elif packet_name == ScreenPacket.get_id():
            packet = ScreenPacket.deserialize(packet_data)
            data = packet.encoded_img
            np_arr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is not None:
                self.gui.show_img(frame)

    def send_to_all_clients(self, packet: BasePacket):
        packet_data = serialize_packet(packet)
        for i in list(self.clients):  # list, чтобы можно было изменять словарь в итерации
            client_socket = self.clients[i]
            try:
                client_socket.send(packet_data)
            except ConnectionError:
                self.clients.pop(i)
                Logger.log(f"{len(self.clients)}) Отключен {client_socket.getpeername()}")

    def start_listen_actions(self):
        return
        # self.keyboard_listener = self.run_keyboard_listener()
        # self.mouse_listener = self.run_mouse_listener()

    def stop_listen_actions(self):
        return
        self.keyboard_listener.stop()
        self.mouse_listener.stop()

    # def run_keyboard_listener(self):
    #     from pynput import keyboard
    #     def on_press(key):
    #         if isinstance(key, keyboard.Key):
    #             key = key.value
    #         self.send_to_all_clients(KeyboardPressPacket(key.vk))
    #
    #     def on_release(key):
    #         if isinstance(key, keyboard.Key):
    #             key = key.value
    #         self.send_to_all_clients(KeyboardReleasePacket(key.vk))
    #
    #     listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    #     listener.start()
    #     return listener

    # def run_mouse_listener(self):
    #     from pynput import mouse
    #     monitor = screeninfo.get_monitors()[0]
    #     screen_width, screen_height = monitor.width, monitor.height
    #
    #     def on_move(x, y):
    #         self.send_to_all_clients(
    #             MouseMovementAbsolutePercentagePacket(x / screen_width, y / screen_height))
    #
    #     def on_click(x, y, magic_button, pressed):
    #         magic_to_button_index = {(4, 2, 0): 1, (64, 32, 0): 2, (16, 8, 0): 3}
    #         button = magic_to_button_index.get(magic_button.value)
    #         if button is None:
    #             Logger.log("unknown mouse button pressed/released: {}".format(magic_button))
    #             return
    #         if pressed:
    #             self.send_to_all_clients(MousePressPacket(button))
    #         else:
    #             self.send_to_all_clients(MouseReleasePacket(button))
    #
    #     def on_scroll(x, y, dx, dy):
    #         self.send_to_all_clients(MouseScrollPacket(dx, dy))
    #
    #     listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    #     listener.start()
    #     return listener

    def update_all_clients(self, path_to_file):
        with open(path_to_file, 'rb') as file:
            self.send_to_all_clients(UpdateClientPacket(file.read()))
        # после рассылки, чтобы было актуальное число клиентов
        self.update_all_clients_data = UpdateAllClientsData(list(self.clients.keys()))

    def clients_startup(self, is_add):
        self.send_to_all_clients(StartupPacket(is_add))

    def find_func(self, ip: str, find_type: typing.Literal["sound", "video", "all"]) -> bool:
        if ip not in self.clients:
            return False
        self.clients[ip].send(serialize_packet(FindPacket(find_type, self.config.find_sound_volume)))
        return True


class ClientObject:
    def __init__(self, name, socket):
        self.name = name
        self.socket = socket


if __name__ == "__main__":
    CoreConstants.init()
    Logger.log(CoreConstants.greeting("Server"))
    app = QApplication(sys.argv)

    try:
        server = Server()
        server.init()
    except KeyboardInterrupt:
        server.stop()  # noqa
        exit()
    except:
        Logger.error("КРИТИЧЕСКАЯ ОШИБКА, пожалуйста, напишите автору")
        Logger.error(traceback.format_exc())
        Logger.log("Рестарт через 5 секунд...")
        time.sleep(5)

    server.gui.show()
    sys.exit(app.exec_())

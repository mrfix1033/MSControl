import json
import os
import shutil
import sys
import traceback

from src.core import Network, CoreConstants
from src.core.Exceptions import LastReleaseAlreadyInstalled
from src.core.Loging import Logger


class Updater:
    def __init__(self, version, is_client: bool):
        self.version = version
        self.release = None
        self.is_client = is_client

    def check_update(self):
        """
        :return: None - если установлена последняя версия, dict (release) - если есть версия новее
        """
        url_releases = f"https://api.github.com/repos/mrfix1033/{CoreConstants.program_name}/releases"
        try:
            with Network.get_client_session() as session:
                with session.get(url=url_releases, timeout=5) as response:
                    text = response.text
                    releases = json.loads(text)
                    last_release = releases[0]
            if not last_release["draft"] \
                    and not last_release["prerelease"] \
                    and last_release["tag_name"] != self.version:
                self.release = last_release
                Logger.log("Доступна новая версия программы (текущая: {}) (новая: {}), напишите update для обновления"
                      .format(self.version, self.release["tag_name"]))
            else:
                Logger.log("Установлена последняя версия")
        except KeyError:
            Logger.log("Слишком частый запрос обновлений, попробуйте позже")
        except:
            Logger.warn("Не удалось запросить обновления")
            Logger.error(traceback.format_exc())
            return

    def update(self) -> bool:
        if self.release is None:
            self.check_update()
            if self.release is None:
                raise LastReleaseAlreadyInstalled()
        client_or_server = "slave" if self.is_client else "master"
        platform_to_extension = {"win32": ".exe"}
        need_asset = f"ActionMulticast-{client_or_server}-{sys.platform}{platform_to_extension[sys.platform]}"
        Logger.log(f"Требуемый файл: {need_asset}")
        for asset in self.release["assets"]:
            if asset["name"] == need_asset:
                download_url = asset["browser_download_url"]
                save_path = os.path.join(os.getenv('TEMP'), need_asset)
                Logger.log("Загрузка...")
                code = Network.download_file(download_url, save_path)
                if code is not None:
                    Logger.log(f"Что-то пошло не так при загрузке файла, HTTP-code: {code}")
                    return False
                path_for_old = sys.executable + ".old"
                if os.path.exists(path_for_old):
                    os.remove(path_for_old)
                shutil.move(sys.executable, path_for_old)
                shutil.move(save_path, sys.executable)
                Logger.log("Обновление загружено. Оно будет установлено после перезапуска")
                return True
        else:
            Logger.log("Отсутствует подходящая версия")
            return False

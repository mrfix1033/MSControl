from src.core.Loging import Logger


class UpdateAllClientsData:
    def __init__(self, client_ips: list[str]):
        self.client_ips = client_ips
        self.updated_ips: list[str] = []
        self.failed_ips: list[str] = []

    def handle(self, ip, is_successful):
        if is_successful:
            self.updated_ips.append(ip)
            Logger.log(self.get_stat(), "Клиент обновлен", ip)
        else:
            self.failed_ips.append(ip)
            Logger.warn(self.get_stat(), "Ошибка у клиента при обновлении", ip)

    def get_stat(self) -> str:
        return f"({len(self.updated_ips)}/{len(self.failed_ips)}/{self.get_remains_count()}/{len(self.client_ips)})"

    def get_remains_count(self) -> int:
        return len(self.client_ips) - len(self.updated_ips) - len(self.failed_ips)

import os
import time


class VPN:
    def __init__(self):
        self.vpn_name = "Surfshark. WireGuard"

    def start(self):
        """  start vpn """
        os.system("scutil --nc start '{}'".format(self.vpn_name))
        time.sleep(15)

    def stop(self):
        """  stop vpn """
        os.system("scutil --nc stop '{}'".format(self.vpn_name))
        time.sleep(10)

    def re_start(self):
        """  restart vpn """
        self.stop()
        self.start()

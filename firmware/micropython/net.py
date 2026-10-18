# Join home Wi-Fi, or start the prop's own hotspot if that fails.
import network
import time
import config


def connect(timeout_s=10):
    try:
        network.hostname(config.HOSTNAME)   # answers as <hostname>.local
    except Exception:
        pass
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        t0 = time.time()
        while not sta.isconnected() and time.time() - t0 < timeout_s:
            time.sleep_ms(250)
    if sta.isconnected():
        ip = sta.ifconfig()[0]
        print("Online: http://%s  (or http://%s.local)" % (ip, config.HOSTNAME))
        return ip, False
    sta.active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=config.AP_SSID, password=config.AP_PASSWORD, authmode=3)
    ip = ap.ifconfig()[0]
    print('No router. Hotspot "%s" -> http://%s' % (config.AP_SSID, ip))
    return ip, True

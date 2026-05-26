"""
HyperX Cloud Core Wireless - Battery Level Checker
Пытается получить уровень заряда наушников через разные методы.
"""

import subprocess
import re
import sys

def method1_powershell_bt():
    """Метод 1: PowerShell - поиск Bluetooth устройств с батареей"""
    print("=" * 60)
    print("Метод 1: Поиск Bluetooth устройств через PowerShell")
    print("=" * 60)
    
    ps_script = """
    $devices = Get-PnpDevice -Class Bluetooth | Where-Object { $_.FriendlyName -match 'Hyper|Cloud|Headphone|Headset' -or $_.Class -eq 'Bluetooth' }
    $devices | Select-Object FriendlyName, Status, Class, InstanceId | Format-Table -AutoSize
    """
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True, timeout=10
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:300])
    except Exception as e:
        print(f"  Ошибка: {e}")

def method2_powershell_battery():
    """Метод 2: PowerShell - поиск батареи у Bluetooth устройств через разные API"""
    print("=" * 60)
    print("Метод 2: Поиск информации о батарее Bluetooth-устройств")
    print("=" * 60)
    
    ps_script = """
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
    
    function Await($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }
    
    [Windows.Devices.Bluetooth.BluetoothDevice, Windows.Devices.Bluetooth, ContentType = WindowsRuntime] | Out-Null
    
    $selector = [Windows.Devices.Bluetooth.BluetoothDevice]::GetDeviceSelector()
    $devices = Await ([Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($selector)) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Enumeration.DeviceInformation]])
    
    foreach ($device in $devices) {
        $btDevice = Await ([Windows.Devices.Bluetooth.BluetoothDevice]::FromIdAsync($device.Id)) ([Windows.Devices.Bluetooth.BluetoothDevice])
        Write-Host "Device: $($device.Name) Id: $($device.Id)"
        if ($btDevice.BatteryReport) {
            Write-Host "  Battery Level: $($btDevice.BatteryReport.ChargeRateInMilliwatts)"
        }
    }
    """
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True, timeout=15
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:500])
    except Exception as e:
        print(f"  Ошибка: {e}")

def method3_devices_with_battery():
    """Метод 3: Поиск через устройства с батареей в системе"""
    print("=" * 60)
    print("Метод 3: Поиск устройств с батареей через WMI/PnP")
    print("=" * 60)
    
    ps_script = """
    Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Hyper|Cloud|Headphone|Headset|Audio' -and $_.Status -eq 'OK' } | Select-Object FriendlyName, Class, DeviceID | Format-Table -AutoSize
    """
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True, timeout=10
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:300])
    except Exception as e:
        print(f"  Ошибка: {e}")

def method4_hid_devices():
    """Метод 4: Поиск HID устройств HyperX"""
    print("=" * 60)
    print("Метод 4: Поиск HID устройств HyperX/Cloud")
    print("=" * 60)
    
    ps_script = """
    Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Hyper|Cloud|Kingston' } | Select-Object FriendlyName, Class, Status, DeviceID | Format-Table -AutoSize
    """
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True, timeout=10
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:300])
    except Exception as e:
        print(f"  Ошибка: {e}")

def method5_powercfg_battery_report():
    """Метод 5: Проверка battery-report.xml на наличие Bluetooth устройств"""
    print("=" * 60)
    print("Метод 5: Парсинг battery-report.xml")
    print("=" * 60)
    
    try:
        # Создаем отчет
        subprocess.run(['powercfg', '/batteryreport', '/output', 'battery-report.xml'], 
                      capture_output=True, text=True, timeout=10)
        
        # Читаем его
        with open('battery-report.xml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем Bluetooth/беспроводные устройства
        if 'Bluetooth' in content or 'Hyper' in content or 'Cloud' in content or 'Headphone' in content:
            print("  Найдены упоминания:")
            for line in content.split('\n'):
                if any(word in line.lower() for word in ['bluetooth', 'hyper', 'cloud', 'headphone', 'headset', 'wireless', 'battery']):
                    print(f"  {line.strip()}")
        else:
            print("  В battery-report.xml нет информации о Bluetooth устройствах")
            
    except Exception as e:
        print(f"  Ошибка: {e}")

def method6_btbatt():
    """Метод 6: Попробуем найти btbatt.sys или информацию через Windows.Devices.Bluetooth"""
    print("=" * 60)
    print("Метод 6: Проверка через Windows Bluetooth API (C# скрипт)")
    print("=" * 60)
    
    # Попробуем через Python напрямую ctypes
    try:
        import ctypes
        from ctypes import wintypes
        
        # Bluetooth API constants
        BLUETOOTH_MAX_NAME_SIZE = 248
        HFDI_RADIO = 1
        
        class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("Address", ctypes.c_ulonglong),
                ("ulClassofDevice", wintypes.ULONG),
                ("fConnected", ctypes.c_bool),
                ("fRemembered", ctypes.c_bool),
                ("fAuthenticated", ctypes.c_bool),
                ("stLastSeen", ctypes.c_longlong),
                ("stLastUsed", ctypes.c_longlong),
                ("szName", ctypes.c_wchar * BLUETOOTH_MAX_NAME_SIZE),
            ]
        
        print("  ctypes работает, но API Bluetooth на C уровне может не давать заряд")
        print("  (заряд батареи - это высокоуровневая функция Windows)")
        
    except ImportError:
        print("  ctypes не найден")
    except Exception as e:
        print(f"  Ошибка: {e}")

def method7_check_audio_devices():
    """Метод 7: Проверка аудио устройств в системе"""
    print("=" * 60)
    print("Метод 7: Аудио устройства (включая беспроводные)")
    print("=" * 60)
    
    ps_script = """
    Add-Type -AssemblyName System.Core
    
    $devices = @()
    Get-PnpDevice | Where-Object { $_.Class -eq 'AudioEndpoint' -or $_.Class -eq 'Media' -or $_.Class -eq 'Sound' } | ForEach-Object {
        $devices += [PSCustomObject]@{
            Name = $_.FriendlyName
            Class = $_.Class
            Status = $_.Status
            DeviceID = $_.DeviceID
        }
    }
    $devices | Format-Table -AutoSize
    """
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True, timeout=10
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[:300])
    except Exception as e:
        print(f"  Ошибка: {e}")


def method8_hidapi_scan():
    """Метод 8: Сканирование HID устройств через hidapi"""
    print("=" * 60)
    print("Метод 8: Сканирование HID устройств через hidapi")
    print("=" * 60)
    
    try:
        import hid
        
        # Перечисляем все HID устройства
        devices = hid.enumerate()
        
        found_hyperx = False
        for dev in devices:
            name = f"{dev.get('manufacturer_string', '')} {dev.get('product_string', '')}"
            if any(word.lower() in name.lower() for word in ['hyper', 'cloud', 'kingston', 'headphone', 'headset']):
                found_hyperx = True
                print(f"  Найдено устройство:")
                print(f"    Производитель: {dev.get('manufacturer_string', 'N/A')}")
                print(f"    Продукт: {dev.get('product_string', 'N/A')}")
                print(f"    Vendor ID: 0x{dev.get('vendor_id', 0):04X}")
                print(f"    Product ID: 0x{dev.get('product_id', 0):04X}")
                print(f"    Usage Page: {dev.get('usage_page', 0)}")
                print(f"    Usage: {dev.get('usage', 0)}")
                print(f"    Path: {dev.get('path', 'N/A')}")
                print()
        
        if not found_hyperx:
            print("  Устройства HyperX/Cloud не найдены через HID")
            # Покажем все HID устройства с manufacturer_string
            print()
            print("  Все HID устройства в системе:")
            for dev in devices[:20]:  # покажем первые 20
                name = f"{dev.get('manufacturer_string', '')} {dev.get('product_string', '')}"
                if name.strip():
                    print(f"    VID:0x{dev.get('vendor_id', 0):04X} PID:0x{dev.get('product_id', 0):04X} - {name}")
        
    except ImportError:
        print("  hidapi не установлен. Установи: pip install hidapi")
    except Exception as e:
        print(f"  Ошибка: {e}")


if __name__ == '__main__':
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Поиск уровня заряда HyperX Cloud Core Wireless ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    method1_powershell_bt()
    print()
    method3_devices_with_battery()
    print()
    method4_hid_devices()
    print()
    method7_check_audio_devices()
    print()
    method8_hidapi_scan()
    print()
    method5_powercfg_battery_report()
    print()
    method6_btbatt()
    print()
    
    print("=" * 60)
    print("Готово! Если ни один метод не показал заряд,")
    print("попробуйте HyperX NGENUITY Software от Kingston")
    print("или установите: pip install bleak (для BLE устройств)")
    print("=" * 60)
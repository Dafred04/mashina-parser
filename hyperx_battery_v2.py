"""
HyperX Cloud Core Wireless - Battery Level Checker v2
Попытка прочитать заряд через HID и BLE
"""

import hid
import time

def read_hid_battery():
    """Чтение заряда напрямую через HID"""
    print("=" * 60)
    print("Попытка прочитать заряд через HID")
    print("=" * 60)
    
    VENDOR_ID = 0x0951
    PRODUCT_ID = 0x173F
    
    try:
        devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
        
        if not devices:
            print("  Устройство не найдено")
            return None
        
        for dev_info in devices:
            path = dev_info.get('path')
            if not path:
                continue
                
            print(f"  Найдено: {dev_info.get('product_string')}")
            print(f"  Usage Page: {dev_info.get('usage_page')}, Usage: {dev_info.get('usage')}")
            print(f"  Path: {path}")
            
            try:
                dev = hid.device()
                dev.open_path(path)
                print(f"  ✅ Открыто: {dev.get_manufacturer_string()} {dev.get_product_string()}")
                
                dev.set_nonblocking(True)
                
                # Пробуем разные report IDs
                for report_id in [0x04, 0x06, 0x08, 0x03, 0x05, 0x00]:
                    try:
                        # Send feature report or output report
                        buf = [report_id] + [0] * 63
                        try:
                            dev.write(bytes(buf))
                            time.sleep(0.05)
                        except Exception as e:
                            print(f"    Report 0x{report_id:02X}: write error - {e}")
                            continue
                        
                        time.sleep(0.1)
                        data = dev.read(64, timeout_ms=300)
                        if data and len(data) > 0:
                            print(f"    Report 0x{report_id:02X}: raw = {list(data[:16])} ({len(data)} bytes)")
                            if report_id == 0x00:
                                # byte[1] часто заряд для HyperX
                                if 0 < data[1] <= 100:
                                    print(f"      ⚡ Byte[1] = {data[1]}% ⬅ возможно заряд!")
                            for i in range(min(16, len(data))):
                                if 0 < data[i] <= 100:
                                    print(f"      Byte[{i}] = {data[i]} (может быть зарядом)")
                        else:
                            print(f"    Report 0x{report_id:02X}: нет данных")
                    except Exception as e:
                        print(f"    Report 0x{report_id:02X}: ошибка - {e}")
                
                dev.close()
                print()
                
            except Exception as e:
                print(f"  ❌ Ошибка открытия: {e}\n")
        
        return None
        
    except Exception as e:
        print(f"  Ошибка: {e}")
        return None


def try_ble_battery():
    """Попытка через BLE (на случай если наушники в BLE режиме)"""
    print("\n" + "=" * 60)
    print("Попытка через BLE (bleak)")
    print("=" * 60)
    
    try:
        import asyncio
        from bleak import BleakScanner
        
        async def scan():
            print("  Сканирование BLE устройств (5 секунд)...")
            devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
            
            found = False
            for addr, (device, adv_data) in devices.items():
                name = device.name or "No name"
                if any(w in name.lower() for w in ['hyper', 'cloud', 'kingston', 'headphone']):
                    found = True
                    print(f"\n  Найдено: {name} [{addr}]")
                    
                    if adv_data.service_uuids:
                        print(f"  Service UUIDs: {adv_data.service_uuids}")
                        if '0000180f-0000-1000-8000-00805f9b34fb' in str(adv_data.service_uuids).lower():
                            print("  ✅ Поддерживает Battery Service!")
                    
                    if adv_data.manufacturer_data:
                        for mid, mdata in adv_data.manufacturer_data.items():
                            print(f"  Manufacturer 0x{mid:04X}: {list(mdata)}")
                    
                    if hasattr(adv_data, 'rssi') and adv_data.rssi:
                        print(f"  RSSI: {adv_data.rssi} dBm")
                
            if not found:
                print("\n  Устройства HyperX/Cloud по BLE не найдены")
            
        asyncio.run(scan())
        
    except ImportError:
        print("  bleak не установлен")
    except Exception as e:
        print(f"  Ошибка: {e}")


def try_windows_api_battery():
    """Попытка через Windows.Devices.Bluetooth API"""
    print("\n" + "=" * 60)
    print("Попытка через Windows Bluetooth API")
    print("=" * 60)
    
    ps_script = r"""
    Add-Type -AssemblyName System.Runtime.WindowsRuntime 
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
    function Await($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }
    
    [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null
    
    try {
        $selector = [Windows.Devices.Bluetooth.BluetoothDevice]::GetDeviceSelectorFromPairingState($true)
        $devices = Await ([Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($selector)) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Enumeration.DeviceInformation]])
        Write-Host "Найдено Bluetooth устройств (сопряжённых): $($devices.Count)"
        foreach ($d in $devices) { Write-Host "  $($d.Name)" }
    } catch { Write-Host "BluetoothDevice error: $_" }
    
    # Попробуем через Battery API
    try {
        [Windows.Devices.Power.Battery,Windows.Devices.Power,ContentType=WindowsRuntime] | Out-Null
        $batteries = [Windows.Devices.Power.Battery]::AggregateBattery
        Write-Host "`nBattery report: $($batteries.GetReport())"
    } catch { Write-Host "Battery API error: $_" }
    """
    
    import subprocess
    try:
        result = subprocess.run(['powershell', '-NoProfile', '-Command', ps_script],
                              capture_output=True, text=True, timeout=30)
        out = result.stdout.strip()
        err = result.stderr.strip()
        if out:
            print(out)
        if err:
            for line in err.split('\n'):
                print(f"  PWSE: {line.strip()}")
    except subprocess.TimeoutExpired:
        print("  Тайм-аут (30 сек)")
    except Exception as e:
        print(f"  Ошибка: {e}")


def try_ngenuity_style_request():
    """Чтение как HyperX NGENUITY через vendor-specific HID feature reports"""
    print("\n" + "=" * 60)
    print("Попытка прочитать через Feature Reports (как NGENUITY)")
    print("=" * 60)
    
    try:
        devices = hid.enumerate(0x0951, 0x173F)
        for dev_info in devices:
            path = dev_info.get('path')
            if not path:
                continue
            
            print(f"\n  Устройство: {dev_info.get('product_string')}")
            
            try:
                dev = hid.device()
                dev.open_path(path)
                
                # HyperX NGENUITY использует vendor-defined feature reports
                # Report ID 0x80 часто для получения статуса/батареи
                feature_reports = {
                    # (report_id, report_size)
                    "Status": (0x80, 64),
                    "Battery": (0x81, 64),
                    "Info": (0x82, 64),
                }
                
                for name, (report_id, size) in feature_reports.items():
                    try:
                        # Feature report через send_feature_report
                        buf = [report_id] + [0] * (size - 1)
                        dev.send_feature_report(bytes(buf))
                        time.sleep(0.1)
                        
                        data = dev.get_feature_report(report_id, size)
                        if data:
                            print(f"  {name} (RF 0x{report_id:02X}): {list(data[:20])}...")
                            if 0 < data[1] <= 100:
                                print(f"    ⚡ Byte[1] = {data[1]}% (заряд)")
                            if 0 < data[2] <= 100:
                                print(f"    Byte[2] = {data[2]}%")
                        else:
                            print(f"  {name} (RF 0x{report_id:02X}): пусто")
                    except Exception as e:
                        print(f"  {name} (RF 0x{report_id:02X}): ошибка - {e}")
                
                dev.close()
                
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                
    except Exception as e:
        print(f"  Ошибка: {e}")


if __name__ == '__main__':
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  HyperX Cloud Core Wireless - Battery Check v2  ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    # 1. HID output reports
    read_hid_battery()
    
    # 2. HID feature reports (как NGENUITY)
    try_ngenuity_style_request()
    
    # 3. Windows API
    try_windows_api_battery()
    
    # 4. BLE
    try_ble_battery()
    
    print()
    print("=" * 60)
    print("Не нашли заряд? Попробуй:")
    print("  1. HyperX NGENUITY (официальная программа)")
    print("     https://hyperx.com/pages/ngenuity")
    print("  2. Или зайди в Параметры > Bluetooth и устройства > Устройства")
    print("=" * 60)